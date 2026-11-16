"""Glue job tlc-preparacion: prepara un mes de un dataset de raw/ a trusted/ (Punto 4).

Argumentos: --dataset {yellow,green,hvfhv,taxi_zones} --mes YYYY-MM (na para taxi_zones) --bucket.
contrato.py y pendientes.py llegan por --extra-py-files.

  1. Lista la partición de raw: tiene que haber exactamente un Parquet.
  2. Valida el esquema contra el contrato. Si no cumple, falla sin tocar trusted.
  3. Borra el control del mes: si algo falla de aquí en adelante, el mes queda pendiente.
  4. Castea y renombra, agrega derivadas y banderas, y sobrescribe la partición de detalle.
  5. Relee lo escrito y compara el conteo con raw. Si no coincide, falla sin control.
  6. Solo servicios: desde el detalle escrito, sobrescribe la partición de viajes y compara su conteo.
  7. Escribe el control.

Ninguna fila se borra: la calidad queda en las banderas.
"""
import json
import math
import sys
from datetime import datetime, timezone

import boto3
from awsglue.utils import getResolvedOptions
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

import contrato
import pendientes as layout

BYTES_POR_ARCHIVO = 256 * 2**20


def archivo_raw(s3, bucket, dataset, mes):
    """(clave, bytes, LastModified) del único Parquet de la partición de raw."""
    if dataset == "taxi_zones":
        o = s3.head_object(Bucket=bucket, Key=layout.CLAVE_ZONAS_RAW)
        return layout.CLAVE_ZONAS_RAW, o["ContentLength"], o["LastModified"]
    r = s3.list_objects_v2(Bucket=bucket, Prefix=layout.prefijo_raw(dataset, mes))
    archivos = [o for o in r.get("Contents", []) if o["Key"].endswith(".parquet")]
    if len(archivos) != 1:
        raise RuntimeError(f"{dataset} {mes}: se esperaba 1 Parquet en raw y hay {len(archivos)}")
    o = archivos[0]
    return o["Key"], o["Size"], o["LastModified"]


def detalle(df, dataset, mes):
    """Contrato aplicado: nombres y tipos canónicos, derivadas y banderas (nunca NULL)."""
    presentes = set(df.columns)
    columnas = [
        (F.col(origen) if origen in presentes else F.lit(None)).cast(tipo).alias(destino)
        for origen, (destino, tipo, _) in contrato.DETALLE[dataset].items()
    ]
    df = df.select(*columnas)
    for nombre, expr in contrato.derivadas(dataset).items():
        df = df.withColumn(nombre, F.expr(expr))
    for nombre, expr in contrato.banderas(dataset, mes).items():
        df = df.withColumn(nombre, F.coalesce(F.expr(expr), F.lit(False)))
    return df


def viajes(spark, detalle_escrito, bucket, dataset):
    """Proyección común de viajes, con las zonas de origen y destino por join broadcast (265 filas).

    Las zonas salen de raw, no de trusted/taxi_zones, para no depender del orden en que se prepara cada dataset.
    Un ID sin zona queda con las columnas de zona en NULL.
    """
    zonas = spark.read.parquet(f"s3://{bucket}/{layout.CLAVE_ZONAS_RAW}")
    df = detalle_escrito
    for lado in ("pu", "do"):
        z = zonas.select(F.col("LocationID").cast("int").alias(f"_{lado}_id"),
                         *[F.col(origen).alias(f"{lado}_{nombre}") for nombre, origen in contrato.ZONA.items()])
        df = df.join(F.broadcast(z), F.col(f"{lado}locationid") == F.col(f"_{lado}_id"), "left")
    return df.select(*[F.expr(expr).alias(nombre) for nombre, expr in contrato.viajes(dataset).items()])


def main():
    args = getResolvedOptions(sys.argv, ["dataset", "mes", "bucket"])
    dataset, mes, bucket = args["dataset"], args["mes"], args["bucket"]
    run_id = sys.argv[sys.argv.index("--JOB_RUN_ID") + 1] if "--JOB_RUN_ID" in sys.argv else None
    if dataset not in contrato.DETALLE:
        raise ValueError(f"dataset desconocido: {dataset}")

    spark = SparkSession.builder.getOrCreate()
    spark.conf.set("spark.sql.session.timeZone", "UTC")  # derivadas de fecha y hora deterministas
    s3 = boto3.client("s3")

    clave, tamano, modificado = archivo_raw(s3, bucket, dataset, mes)
    raw = spark.read.parquet(f"s3://{bucket}/{clave}")
    errores = contrato.validar(dataset, [(f.name, f.dataType.simpleString()) for f in raw.schema.fields])
    if errores:
        raise RuntimeError(f"{clave} no cumple el contrato: {errores}")
    filas_raw = raw.count()
    if filas_raw == 0:
        raise RuntimeError(f"{clave} está vacío")

    clave_control = layout.clave_control(dataset, mes)
    s3.delete_object(Bucket=bucket, Key=clave_control)

    destino = f"s3://{bucket}/{layout.prefijo_trusted(dataset, mes)}"
    n = max(1, math.ceil(tamano / BYTES_POR_ARCHIVO))
    detalle(raw, dataset, mes).repartition(n).write.mode("overwrite").parquet(destino)

    escrito = spark.read.parquet(destino)
    nombres_banderas = list(contrato.banderas(dataset, mes))
    fila = escrito.agg(
        F.count(F.lit(1)).alias("filas"),
        *[F.sum(F.col(b).cast("long")).alias(b) for b in nombres_banderas],
    ).first()
    if fila["filas"] != filas_raw:
        raise RuntimeError(f"{dataset} {mes}: raw tiene {filas_raw} filas y trusted {fila['filas']}")

    extra = {}
    if dataset in contrato.SERVICIOS:
        destino_viajes = f"s3://{bucket}/{layout.prefijo_trusted('viajes', mes, servicio=dataset)}"
        viajes(spark, escrito, bucket, dataset).repartition(n).write.mode("overwrite").parquet(destino_viajes)
        v = spark.read.parquet(destino_viajes).agg(
            F.count(F.lit(1)).alias("filas"),
            F.sum(F.expr("pu_borough IS NULL OR do_borough IS NULL").cast("long")).alias("sin_zona"),
        ).first()
        if v["filas"] != filas_raw:
            raise RuntimeError(f"{dataset} {mes}: raw tiene {filas_raw} filas y viajes {v['filas']}")
        extra = {"filas_viajes": v["filas"], "sin_zona": int(v["sin_zona"] or 0)}

    # Si la ingesta reemplazó el archivo de raw mientras corría el job, no se escribe el control: el mes
    # queda pendiente y la ejecución siguiente lo rehace con la versión nueva.
    if archivo_raw(s3, bucket, dataset, mes)[1:] != (tamano, modificado):
        raise RuntimeError(f"{clave} cambió durante el job; el mes queda pendiente")

    control = {
        "dataset": dataset,
        "mes": mes,
        "raw": {"clave": clave, "bytes": tamano, "last_modified": modificado.isoformat()},
        "filas_raw": filas_raw,
        "filas_detalle": fila["filas"],
        "archivos_detalle": n,
        **extra,
        "banderas": {b: int(fila[b] or 0) for b in nombres_banderas},
        "esquema_detalle": [[f.name, f.dataType.simpleString()] for f in escrito.schema.fields],
        "job_run_id": run_id,
        "escrito_en": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    s3.put_object(Bucket=bucket, Key=clave_control, Body=json.dumps(control, ensure_ascii=False, indent=1).encode(),
                  ContentType="application/json")
    print(json.dumps(control, ensure_ascii=False))


if __name__ == "__main__":
    main()

"""Ingesta de las fuentes que viven en la VPC (Punto 3). Corre en la EC2; la lanza la Lambda por SSM.

  - yellow: cada yellow_tripdata_YYYY-MM.parquet de la carpeta de la EC2 que no esté en raw/ con el
    mismo tamaño se sube tal cual.
  - green: cada mes de cargas_green se extrae de green_trips a un Parquet. Un mes recargado con
    `simular.py --forzar` cambia su cargado_en y se vuelve a extraer, reemplazando el archivo.
    Las filas extraídas se cuadran contra cargas_green antes de subir.
  - taxi_zones: tabla completa; se sube solo si su contenido cambió.

Sale con código 1 si algo falló, para que SSM y la Lambda lo marquen.
Variables de entorno: TLC_BUCKET, TLC_CARPETA_YELLOW y las de MariaDB que lee fuente.py.
"""
import hashlib
import io
import os
import re
import sys

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
import pymysql
from boto3.exceptions import S3UploadFailedError
from botocore.exceptions import ClientError
from pymysql.constants import FIELD_TYPE

import raw
from fuente import conectar, env  # utilidades del Punto 2 (punto2-fuentes/ec2/fuente.py)

PATRON_YELLOW = re.compile(r"yellow_tripdata_(\d{4}-\d{2})\.parquet")  # ignora los .part del simulador

# Tipo de MariaDB -> tipo de Arrow. Sale del esquema de la tabla, no de los valores: una columna toda
# en NULL (cbd_congestion_fee en 2024, ehail_fee) mantiene su tipo y todos los meses comparten esquema.
TIPOS = {
    FIELD_TYPE.TINY: pa.int64(),
    FIELD_TYPE.SHORT: pa.int64(),
    FIELD_TYPE.INT24: pa.int64(),
    FIELD_TYPE.LONG: pa.int64(),
    FIELD_TYPE.LONGLONG: pa.int64(),
    FIELD_TYPE.FLOAT: pa.float64(),
    FIELD_TYPE.DOUBLE: pa.float64(),
    FIELD_TYPE.DATETIME: pa.timestamp("us"),
    FIELD_TYPE.TIMESTAMP: pa.timestamp("us"),
    FIELD_TYPE.STRING: pa.string(),
    FIELD_TYPE.VAR_STRING: pa.string(),
    FIELD_TYPE.VARCHAR: pa.string(),
}

s3 = boto3.client("s3")


def metadatos(bucket, clave):
    """Metadatos de usuario del objeto, o None si no existe."""
    try:
        return s3.head_object(Bucket=bucket, Key=clave)["Metadata"]
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return None
        raise


def tamanos(bucket, prefijo):
    resultado = {}
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefijo):
        for o in pagina.get("Contents", []):
            resultado[o["Key"]] = o["Size"]
    return resultado


def a_tabla(cur):
    """Resultado de la última consulta del cursor -> tabla de Arrow con tipos del esquema de MariaDB."""
    nombres = [d[0] for d in cur.description]
    faltan = [d[0] for d in cur.description if d[1] not in TIPOS]
    if faltan:
        raise ValueError(f"columnas con tipo de MariaDB sin mapear: {faltan}")
    columnas = list(zip(*cur.fetchall())) or [()] * len(nombres)
    arreglos = [pa.array(col, type=TIPOS[d[1]]) for col, d in zip(columnas, cur.description)]
    return pa.Table.from_arrays(arreglos, names=nombres)


def subir_tabla(bucket, clave, tabla, meta):
    buf = io.BytesIO()
    pq.write_table(tabla, buf)
    s3.put_object(Bucket=bucket, Key=clave, Body=buf.getvalue(), Metadata=meta)
    return buf.tell() / 2**20


# ------------------------------------------------------------------ yellow: archivos de la EC2
def ingerir_yellow(bucket, carpeta, errores):
    existentes = tamanos(bucket, raw.PREFIJO + "yellow/")
    ya = 0
    for nombre in sorted(os.listdir(carpeta)):
        m = PATRON_YELLOW.fullmatch(nombre)
        if not m:
            continue
        ruta = os.path.join(carpeta, nombre)
        clave = raw.clave("yellow", m.group(1), nombre)
        if existentes.get(clave) == os.path.getsize(ruta):
            ya += 1
            continue
        try:
            filas = pq.ParquetFile(ruta).metadata.num_rows
            s3.upload_file(ruta, bucket, clave, ExtraArgs={"Metadata": {"filas": str(filas)}})
            print(f"  yellow {m.group(1)}: {filas} filas, {os.path.getsize(ruta) / 2**20:.1f} MiB -> {clave}")
        except (OSError, pa.ArrowInvalid, ClientError, S3UploadFailedError) as e:
            errores.append(f"yellow {m.group(1)}: {e}")
    print(f"  yellow: {ya} archivos ya estaban en raw")


# ------------------------------------------------------------------ green: MariaDB
def ingerir_green(con, bucket, errores):
    with con.cursor() as cur:
        cur.execute("SELECT mes, filas, cargado_en FROM cargas_green ORDER BY mes")
        cargas = cur.fetchall()
    ya = 0
    for mes, filas, cargado_en in cargas:
        clave = raw.clave("green", mes, f"green_tripdata_{mes}.parquet")
        version = cargado_en.isoformat()
        meta = metadatos(bucket, clave)
        if meta and meta.get("cargado-en") == version:
            ya += 1
            continue
        with con.cursor() as cur:
            cur.execute("SELECT * FROM green_trips WHERE mes_archivo = %s ORDER BY trip_id", (mes,))
            tabla = a_tabla(cur)
        if tabla.num_rows != filas:
            errores.append(f"green {mes}: {tabla.num_rows} filas en green_trips y {filas} en cargas_green; no se sube")
            continue
        mib = subir_tabla(bucket, clave, tabla, {"filas": str(filas), "cargado-en": version})
        accion = "reemplazado" if meta else "nuevo"
        print(f"  green {mes}: {filas} filas, {mib:.1f} MiB -> {clave} ({accion})")
    print(f"  green: {ya} meses ya estaban en raw")


def ingerir_zonas(con, bucket):
    with con.cursor() as cur:
        cur.execute("SELECT * FROM taxi_zones ORDER BY LocationID")
        tabla = a_tabla(cur)
    huella = hashlib.sha256(repr(tabla.to_pylist()).encode()).hexdigest()[:16]
    meta = metadatos(bucket, raw.CLAVE_ZONAS)
    if meta and meta.get("huella") == huella:
        print(f"  taxi_zones: sin cambios ({tabla.num_rows} filas)")
        return
    subir_tabla(bucket, raw.CLAVE_ZONAS, tabla, {"filas": str(tabla.num_rows), "huella": huella})
    print(f"  taxi_zones: {tabla.num_rows} filas -> {raw.CLAVE_ZONAS}")


def main():
    bucket = env("TLC_BUCKET")
    errores = []
    print("Ingesta de la EC2")
    try:
        ingerir_yellow(bucket, env("TLC_CARPETA_YELLOW"), errores)
    except (OSError, ClientError) as e:
        errores.append(f"yellow: {e}")
    try:
        # Toda la lectura va en una sola transacción (REPEATABLE READ de InnoDB): cargas_green y
        # green_trips se leen del mismo instante aunque el simulador esté cargando un mes.
        con = conectar()
        try:
            ingerir_zonas(con, bucket)
            ingerir_green(con, bucket, errores)
        finally:
            con.close()
    except (pymysql.MySQLError, ClientError, ValueError) as e:
        errores.append(f"mariadb: {e}")
    for e in errores:
        print(f"  ERROR {e}", file=sys.stderr)
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()

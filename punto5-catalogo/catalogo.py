"""Catálogo de trusted en el Glue Data Catalog (Punto 5). Es idempotente: crea lo que falta y no borra nada.

Tablas: yellow, green, hvfhv (detalle), viajes y taxi_zones, en la base RECURSOS["glue_base"].
  - Columnas y tipos: del esquema_detalle que escribe el job en cada control, y para viajes, de
    contrato.viajes() sobre ese esquema. No hay crawler (convención "Catalogación").
  - Particiones: solo las de los meses que tienen control, registradas con batch_create_partition.
    year, month y servicio van como string, con el mismo texto de la ruta ("01").

Lo usan desplegar.py (corrida inicial) y la Lambda tlc-catalogo, último paso de la state machine
tlc-preparacion. La Lambda recibe BUCKET y BASE por variables de entorno.
"""
import json
import os
import re

import boto3

import contrato
import pendientes as layout

CONTROL_MES = re.compile(re.escape(layout.CONTROL) + r"([^/]+)/(\d{4})-(\d{2})\.json$")
CONTROL_ZONAS = layout.clave_control("taxi_zones", layout.SIN_MES)
COLUMNAS_ZONA = {f"{lado}_{n}" for lado in ("pu", "do") for n in contrato.ZONA}
PARQUET = {
    "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
    "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
    "SerdeInfo": {"SerializationLibrary": "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"},
}


def claves_particion(tabla):
    if tabla == "taxi_zones":
        return []
    return (["servicio"] if tabla == "viajes" else []) + ["year", "month"]


def columnas_viajes(servicio, esquema):
    """Columnas de viajes con tipo, desde el esquema del detalle del servicio: [(nombre, tipo)]."""
    tipos = dict(esquema)
    cols = []
    for nombre, expr in contrato.viajes(servicio).items():
        if expr in tipos:
            cols.append((nombre, tipos[expr]))  # columna copiada del detalle
        elif expr.startswith("coalesce("):
            cols.append((nombre, "double"))  # suma de componentes de tarifa
        elif nombre == "compania" or expr in COLUMNAS_ZONA:
            cols.append((nombre, "string"))  # literal o CASE, y columnas de zona del join
        else:
            raise ValueError(f"viajes.{nombre} = {expr}: no se sabe su tipo; agregarlo a columnas_viajes")
    return cols


def columnas(controles):
    """{tabla: [(nombre, tipo)]} desde {dataset: esquema_detalle}. viajes exige el mismo esquema en todos."""
    tablas = {ds: [tuple(c) for c in esq] for ds, esq in controles.items()}
    por_servicio = {ds: columnas_viajes(ds, tablas[ds]) for ds in contrato.SERVICIOS if ds in tablas}
    if por_servicio:
        distintos = {ds for ds, cols in por_servicio.items() if cols != next(iter(por_servicio.values()))}
        if distintos:
            raise ValueError(f"viajes sale con tipos distintos en {sorted(distintos)}: {por_servicio}")
        tablas["viajes"] = next(iter(por_servicio.values()))
    return tablas


def particiones(claves_control):
    """{tabla: {valores}} desde las claves de control. Cada mes de un servicio da una partición en su
    tabla de detalle y otra en viajes."""
    resultado = {}
    for clave in claves_control:
        m = CONTROL_MES.match(clave)
        if not m:
            continue
        ds, anio, mes = m.groups()
        resultado.setdefault(ds, set()).add((anio, mes))
        if ds in contrato.SERVICIOS:
            resultado.setdefault("viajes", set()).add((ds, anio, mes))
    return resultado


def ubicacion(bucket, tabla, valores=()):
    partes = [f"{k}={v}" for k, v in zip(claves_particion(tabla), valores)]
    return f"s3://{bucket}/" + layout.TRUSTED + "/".join([tabla, *partes]) + "/"


def entrada_tabla(bucket, tabla, cols):
    return {
        "Name": tabla,
        "TableType": "EXTERNAL_TABLE",
        "Parameters": {"classification": "parquet", "EXTERNAL": "TRUE"},
        "PartitionKeys": [{"Name": k, "Type": "string"} for k in claves_particion(tabla)],
        "StorageDescriptor": {"Columns": [{"Name": n, "Type": t} for n, t in cols],
                              "Location": ubicacion(bucket, tabla), **PARQUET},
    }


# --- AWS ---

def asegurar_base(glue, base):
    try:
        glue.create_database(DatabaseInput={"Name": base, "Description": "proyecto2-sd: zona trusted"})
        return "creada"
    except glue.exceptions.AlreadyExistsException:
        return "ya existía"


def asegurar_tabla(glue, base, entrada):
    try:
        glue.create_table(DatabaseName=base, TableInput=entrada)
        return "creada"
    except glue.exceptions.AlreadyExistsException:
        glue.update_table(DatabaseName=base, TableInput=entrada, SkipArchive=True)
        return "actualizada"


def registrar(glue, base, bucket, tabla, sd, valores):
    """Crea las particiones que faltan. Devuelve cuántas creó."""
    existentes = set()
    for pagina in glue.get_paginator("get_partitions").paginate(DatabaseName=base, TableName=tabla):
        existentes |= {tuple(p["Values"]) for p in pagina["Partitions"]}
    faltan = sorted(set(valores) - existentes)
    for i in range(0, len(faltan), 100):  # tope de batch_create_partition
        lote = [{"Values": list(v), "StorageDescriptor": {**sd, "Location": ubicacion(bucket, tabla, v)}}
                for v in faltan[i:i + 100]]
        errores = [e for e in glue.batch_create_partition(DatabaseName=base, TableName=tabla,
                                                          PartitionInputList=lote).get("Errors", [])
                   if e["ErrorDetail"]["ErrorCode"] != "AlreadyExistsException"]
        if errores:
            raise RuntimeError(f"{tabla}: {errores}")
    return len(faltan)


def catalogar(glue, s3, bucket, base):
    """Asegura base, tablas y particiones según los controles de trusted. Devuelve un resumen."""
    claves = sorted(o["Key"] for p in s3.get_paginator("list_objects_v2").paginate(
        Bucket=bucket, Prefix=layout.CONTROL) for o in p.get("Contents", []))
    # El esquema del detalle es el mismo en todos los meses (el job castea al contrato): basta el último.
    ultimo = {}
    for clave in claves:
        m = CONTROL_MES.match(clave)
        if m:
            ultimo[m.group(1)] = clave
        elif clave == CONTROL_ZONAS:
            ultimo["taxi_zones"] = clave
    esquemas = {ds: json.loads(s3.get_object(Bucket=bucket, Key=k)["Body"].read())["esquema_detalle"]
                for ds, k in ultimo.items()}
    resumen = {"base": asegurar_base(glue, base), "tablas": {}}
    parts = particiones(claves)
    for tabla, cols in sorted(columnas(esquemas).items()):
        entrada = entrada_tabla(bucket, tabla, cols)
        estado = asegurar_tabla(glue, base, entrada)
        nuevas = registrar(glue, base, bucket, tabla, entrada["StorageDescriptor"], parts.get(tabla, ()))
        resumen["tablas"][tabla] = {"tabla": estado, "particiones_nuevas": nuevas,
                                    "particiones": len(parts.get(tabla, ()))}
    return resumen


def handler(event, context):
    resumen = catalogar(boto3.client("glue"), boto3.client("s3"), os.environ["BUCKET"], os.environ["BASE"])
    print(json.dumps(resumen))
    return resumen

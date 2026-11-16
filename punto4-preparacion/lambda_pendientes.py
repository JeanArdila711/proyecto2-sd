"""Lambda tlc-preparacion-pendientes: primer estado de la state machine tlc-preparacion.

Lista raw/ y trusted/_control/ y devuelve {"pendientes": [{"dataset", "mes", "workers"}]}.
Variables de entorno (las pone desplegar.py): BUCKET y WORKERS ({dataset: n} en JSON).
"""
import json
import os

import boto3

import pendientes

s3 = boto3.client("s3")


def listar(bucket, prefijo):
    """{clave: LastModified} de todo lo que hay bajo el prefijo."""
    resultado = {}
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefijo):
        for o in pagina.get("Contents", []):
            resultado[o["Key"]] = o["LastModified"]
    return resultado


def handler(event, context):
    bucket = os.environ["BUCKET"]
    lista = pendientes.pendientes(
        listar(bucket, "raw/"), listar(bucket, pendientes.CONTROL), json.loads(os.environ["WORKERS"])
    )
    print(json.dumps({"pendientes": len(lista), "detalle": lista}))
    return {"pendientes": lista}

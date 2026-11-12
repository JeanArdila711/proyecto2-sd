"""Utilidades compartidas por sembrar.py y simulador.py. Corre en la EC2 (Python 3.11).

La configuración llega por variables de entorno que pone el script del portátil
(punto2-fuentes/remoto.py): TLC_DB_HOST, TLC_DB_NAME, TLC_DB_USER, TLC_PARAM_PASSWORD,
TLC_PARAM_MES, TLC_CARPETA_YELLOW, AWS_DEFAULT_REGION.
"""
import os
import shutil
import urllib.request

import boto3
import pymysql

URL_TLC = "https://d37ci6vzurychx.cloudfront.net"


def env(nombre):
    valor = os.environ.get(nombre)
    if not valor:
        raise SystemExit(f"Falta la variable de entorno {nombre}")
    return valor


def ssm():
    return boto3.client("ssm")


def conectar():
    password = ssm().get_parameter(Name=env("TLC_PARAM_PASSWORD"), WithDecryption=True)["Parameter"]["Value"]
    return pymysql.connect(
        host=env("TLC_DB_HOST"),
        user=env("TLC_DB_USER"),
        password=password,
        database=env("TLC_DB_NAME"),
        charset="utf8mb4",
        autocommit=False,
    )


def descargar(url, destino):
    """Descarga a destino.part y renombra al final, para que nadie vea un archivo a medias."""
    parcial = destino + ".part"
    with urllib.request.urlopen(url, timeout=120) as r, open(parcial, "wb") as f:
        shutil.copyfileobj(r, f, length=1024 * 1024)
    os.replace(parcial, destino)

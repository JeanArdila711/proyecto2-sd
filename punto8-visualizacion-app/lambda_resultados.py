"""Punto 8: Lambda detrás de API Gateway que expone los resultados de P1–P6 como JSON.

  GET /resultados              -> lista de preguntas con su título y su ruta
  GET /resultados/{pregunta}   -> {"pregunta", "titulo", "columnas", "filas"} de s3://BUCKET/PREFIJO{pregunta}/resultado.csv

Lee los CSV que deja punto6-analitica-sql/athena.py (los cuatro motores dan los mismos números, comparar.py).
No consulta trusted: Athena cobra por dato escaneado y los resultados ya están calculados.
"""
import csv
import io
import json
import math
import os

import boto3

s3 = boto3.client("s3")
BUCKET, PREFIJO = os.environ["BUCKET"], os.environ["PREFIJO"]
PREGUNTAS = {
    "p1": "¿Cuál es la participación de mercado de taxis amarillos, verdes, Uber y Lyft por borough y por mes?",
    "p2": "¿Cuánto cuesta la milla en taxi amarillo frente a Uber y Lyft, por zona y por hora?",
    "p3": "¿Qué porcentaje de lo que paga el pasajero le llega al conductor en Uber y en Lyft, "
          "y cómo varía por hora y borough?",
    "p4": "¿Cuánto espera un pasajero desde que pide el viaje hasta que lo recogen, por compañía, borough y hora?",
    "p5": "¿Qué se asocia a propinas más altas en taxi amarillo: hora, distancia, zona de origen o viaje al aeropuerto?",
    "p6": "¿Cambió el cobro por congestión (desde el 5 de enero de 2025) la cantidad de viajes hacia la zona "
          "de cobro y el reparto entre taxis y apps?",
}
TEXTO = {"year", "month", "valor", "zona", "borough", "compania", "dimension"}  # el resto son números


def respuesta(codigo, cuerpo):
    return {"statusCode": codigo,
            "headers": {"content-type": "application/json; charset=utf-8", "cache-control": "max-age=300"},
            "body": json.dumps(cuerpo, ensure_ascii=False, allow_nan=False)}


def valor(columna, texto):
    if texto == "":
        return None
    if columna in TEXTO:
        return texto
    numero = float(texto)
    if math.isnan(numero) or math.isinf(numero):
        return None  # NaN no es JSON válido; un 0/0 de un motor llega como null
    return int(numero) if numero.is_integer() else numero


def handler(event, _context):
    pregunta = (event.get("pathParameters") or {}).get("pregunta")
    if pregunta is None:
        return respuesta(200, {"preguntas": [{"id": p, "titulo": t, "ruta": f"/resultados/{p}"}
                                             for p, t in PREGUNTAS.items()]})
    if pregunta not in PREGUNTAS:
        return respuesta(404, {"error": f"No existe la pregunta '{pregunta}'. Use p1 a p6."})
    try:
        cuerpo = s3.get_object(Bucket=BUCKET, Key=f"{PREFIJO}{pregunta}/resultado.csv")["Body"].read()
    except s3.exceptions.NoSuchKey:
        return respuesta(404, {"error": f"Todavía no hay resultados de {pregunta}: corra punto6-analitica-sql/athena.py."})
    filas = list(csv.reader(io.StringIO(cuerpo.decode("utf-8"))))
    columnas = filas[0]
    return respuesta(200, {"pregunta": pregunta, "titulo": PREGUNTAS[pregunta], "columnas": columnas,
                           "filas": [[valor(c, v) for c, v in zip(columnas, f)] for f in filas[1:]]})

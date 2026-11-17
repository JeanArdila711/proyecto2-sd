#!/usr/bin/env python3
"""Verifica el catálogo con Athena: count(*) por tabla y partición contra los controles de trusted.

Uso (desde la raíz del repo): python punto5-catalogo/verificar.py
Termina con código 1 si alguna partición no coincide o falta.
"""
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "punto4-preparacion")]

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

import pendientes as layout  # noqa: E402

CONSULTAS = {
    "yellow": "SELECT year, month, count(*) FROM yellow GROUP BY 1, 2",
    "green": "SELECT year, month, count(*) FROM green GROUP BY 1, 2",
    "hvfhv": "SELECT year, month, count(*) FROM hvfhv GROUP BY 1, 2",
    "viajes": "SELECT servicio, year, month, count(*) FROM viajes GROUP BY 1, 2, 3",
    "taxi_zones": "SELECT count(*) FROM taxi_zones",
}


def athena(cliente, sql):
    qid = cliente.start_query_execution(QueryString=sql, WorkGroup=R["athena_workgroup"],
                                        QueryExecutionContext={"Database": R["glue_base"]})["QueryExecutionId"]
    while (e := cliente.get_query_execution(QueryExecutionId=qid)["QueryExecution"])["Status"]["State"] in (
            "QUEUED", "RUNNING"):
        time.sleep(1)
    if e["Status"]["State"] != "SUCCEEDED":
        raise SystemExit(f"{sql}: {e['Status'].get('StateChangeReason')}")
    filas = []
    for pagina in cliente.get_paginator("get_query_results").paginate(QueryExecutionId=qid):
        filas += [[c.get("VarCharValue") for c in f["Data"]] for f in pagina["ResultSet"]["Rows"]]
    escaneado = e["Statistics"].get("DataScannedInBytes", 0)
    return filas[1:], escaneado  # la primera fila son los encabezados


def esperado(s3, bucket):
    """{tabla: {valores de partición: filas}} desde los controles."""
    r = {t: {} for t in CONSULTAS}
    for p in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=layout.CONTROL):
        for o in p.get("Contents", []):
            c = json.loads(s3.get_object(Bucket=bucket, Key=o["Key"])["Body"].read())
            if c["dataset"] == "taxi_zones":
                r["taxi_zones"][()] = c["filas_detalle"]
                continue
            anio, mes = c["mes"].split("-")
            r[c["dataset"]][(anio, mes)] = c["filas_detalle"]
            r["viajes"][(c["dataset"], anio, mes)] = c["filas_viajes"]
    return r


def main():
    aws = config.sesion(config.cargar())
    s3, cliente = aws.client("s3"), aws.client("athena")
    esp = esperado(s3, config.nombre_bucket(aws))
    malas, total_bytes = [], 0
    print(f"{'tabla':<11} {'particiones':>11} {'filas Athena':>14} {'filas control':>14}  escaneado")
    for tabla, sql in CONSULTAS.items():
        filas, escaneado = athena(cliente, sql)
        total_bytes += escaneado
        obtenido = {tuple(f[:-1]): int(f[-1]) for f in filas}
        distintas = sorted(k for k in esp[tabla].keys() | obtenido.keys()
                           if esp[tabla].get(k) != obtenido.get(k))
        malas += [(tabla, k, esp[tabla].get(k), obtenido.get(k)) for k in distintas]
        # count(*) no decodifica columnas: una fila completa prueba que los tipos del catálogo leen el Parquet
        _, escaneado_fila = athena(cliente, f"SELECT * FROM {tabla} LIMIT 1")
        total_bytes += escaneado_fila
        print(f"{tabla:<11} {len(obtenido):>11} {sum(obtenido.values()):>14,} {sum(esp[tabla].values()):>14,}"
              f"  {escaneado / 2**20:,.1f} MiB")
    print(f"Escaneado en total: {total_bytes / 2**20:,.1f} MiB")
    for tabla, k, e, o in malas:
        print(f"  DIFERENCIA {tabla} {'/'.join(k)}: control {e}, Athena {o}")
    print("OK: Athena coincide con los controles" if not malas else f"{len(malas)} particiones con diferencias")
    sys.exit(1 if malas else 0)


if __name__ == "__main__":
    main()

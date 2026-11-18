#!/usr/bin/env python3
"""Punto 6 en Athena: corre P1–P6 sobre tlc_trusted y deja cada resultado en s3://<bucket>/resultados/punto6/athena/.

Usa el workgroup tlc-consultas del Punto 5. Athena escribe el CSV de cada consulta en athena/ (el lugar de
resultados del workgroup); este script lo copia a resultados/punto6/athena/{pregunta}/resultado.csv, que es
lo que leen comparar.py y el Punto 8.

Uso (desde la raíz del repo):
  python punto6-analitica-sql/athena.py            # las seis
  python punto6-analitica-sql/athena.py p2 p5      # algunas
"""
import argparse
import csv
import io
import sys
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(DIR.parent), str(DIR), str(DIR.parent / "punto5-catalogo")]

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

import consultas  # noqa: E402
import emr_hive  # noqa: E402  (vaciar)


def correr(athena, sql):
    """Ejecuta y espera. Devuelve la QueryExecution terminada; falla si la consulta no salió bien."""
    qid = athena.start_query_execution(QueryString=sql, WorkGroup=R["athena_workgroup"],
                                       QueryExecutionContext={"Database": R["glue_base"]})["QueryExecutionId"]
    while (e := athena.get_query_execution(QueryExecutionId=qid)["QueryExecution"])["Status"]["State"] in (
            "QUEUED", "RUNNING"):
        time.sleep(1)
    if e["Status"]["State"] != "SUCCEEDED":
        raise SystemExit(f"{e['Status']['State']}: {e['Status'].get('StateChangeReason')}")
    return e


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("preguntas", nargs="*", help="p1..p6 (por defecto, todas)")
    args = p.parse_args()
    todas = consultas.preguntas()
    elegidas = args.preguntas or list(todas)
    if desconocidas := set(elegidas) - set(todas):
        raise SystemExit(f"preguntas desconocidas: {sorted(desconocidas)}")

    aws = config.sesion(config.cargar())
    athena, s3 = aws.client("athena"), aws.client("s3")
    bucket = config.nombre_bucket(aws)
    for pregunta in elegidas:  # si una consulta falla, las siguientes no quedan con lo de otra corrida
        emr_hive.vaciar(s3, bucket, f"{consultas.RESULTADOS}athena/{pregunta}/")
    total = 0
    for pregunta in elegidas:
        inicio = time.time()
        e = correr(athena, consultas.render(pregunta, "athena"))
        origen = e["ResultConfiguration"]["OutputLocation"]  # s3://bucket/athena/<id>.csv
        clave_origen = origen.split(f"s3://{bucket}/", 1)[1]
        clave = f"{consultas.RESULTADOS}athena/{pregunta}/resultado.csv"
        s3.copy_object(Bucket=bucket, Key=clave, CopySource={"Bucket": bucket, "Key": clave_origen})
        cuerpo = s3.get_object(Bucket=bucket, Key=clave)["Body"].read().decode("utf-8")
        filas = list(csv.reader(io.StringIO(cuerpo)))
        escaneado = e["Statistics"].get("DataScannedInBytes", 0)
        total += escaneado
        print(f"{pregunta}: {len(filas) - 1} filas, {escaneado / 2**20:,.1f} MiB escaneados, "
              f"{time.time() - inicio:.1f} s -> s3://<bucket>/{clave}")
        for fila in filas[:4]:
            print("    " + " | ".join(fila))
    print(f"Escaneado en total: {total / 2**20:,.1f} MiB")


if __name__ == "__main__":
    main()

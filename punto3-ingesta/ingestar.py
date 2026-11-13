#!/usr/bin/env python3
"""Dispara la ingesta ya mismo y muestra qué hay en la zona raw.

Invoca la misma Lambda que dispara EventBridge, con el mismo evento, así que el resultado es el mismo
que el de una corrida programada; solo no hay que esperar los 5 minutos.

Uso (desde la raíz del repo, después de desplegar.py):
  python punto3-ingesta/ingestar.py             # corre la ingesta y muestra el estado de raw/
  python punto3-ingesta/ingestar.py --estado    # solo el estado de raw/
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from botocore.config import Config  # noqa: E402

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

PARTICION = re.compile(r"raw/([^/]+)/year=(\d{4})/month=(\d{2})/")


def estado(aws, bucket):
    por_dataset = defaultdict(list)  # dataset -> [(mes, bytes)]
    for pagina in aws.client("s3").get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix="raw/"):
        for o in pagina.get("Contents", []):
            m = PARTICION.match(o["Key"])
            if m:
                por_dataset[m.group(1)].append((f"{m.group(2)}-{m.group(3)}", o["Size"]))
            else:
                por_dataset[o["Key"].split("/")[1]].append((None, o["Size"]))
    print(f"Zona raw (s3://{bucket}/raw/)")
    if not por_dataset:
        print("  vacía")
    for dataset, archivos in sorted(por_dataset.items()):
        meses = sorted(m for m, _ in archivos if m)
        rango = f"{meses[0]} .. {meses[-1]}" if meses else "sin partición"
        gib = sum(t for _, t in archivos) / 2**30
        print(f"  {dataset:<11} {len(archivos):>2} archivos  {rango:<18} {gib:6.2f} GiB")


def invocar(aws):
    lam = aws.client("lambda", config=Config(read_timeout=960, retries={"max_attempts": 0}))
    print(f"Invocando {R['lambda_ingesta']} (si hay meses de HVFHV por bajar, tarda unos minutos)…", flush=True)
    try:
        r = lam.invoke(FunctionName=R["lambda_ingesta"], Payload=json.dumps({"desde": R["ingesta_desde"]}))
    except lam.exceptions.TooManyRequestsException:
        print("Ya hay una corrida en curso (la programada). Espera a que termine y usa --estado.")
        return False
    payload = json.loads(r["Payload"].read())
    if "FunctionError" in r:
        try:
            resumen = json.loads(payload["errorMessage"])
        except (KeyError, ValueError):
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return False
    else:
        resumen = payload
    print("HVFHV (URL de la TLC)")
    for linea in resumen["hvfhv"]:
        print(f"  {linea}")
    print(f"EC2 (yellow, green, taxi_zones): {resumen['ec2']}")
    for e in resumen["errores"]:
        print(f"ERROR {e}")
    print()
    return not resumen["errores"]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--estado", action="store_true", help="solo muestra el estado de raw/")
    args = p.parse_args()
    aws = config.sesion(config.cargar())
    ok = True if args.estado else invocar(aws)
    estado(aws, config.nombre_bucket(aws))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Operación manual de la preparación raw -> trusted (Punto 4). También es el plan B del encadenamiento.

Uso (desde la raíz del repo):
  python punto4-preparacion/preparar_local.py --estado                                # pendientes y controles
  python punto4-preparacion/preparar_local.py --ejecutar                              # corre la state machine
  python punto4-preparacion/preparar_local.py --forzar --dataset green --mes 2024-01  # rehace un mes
  python punto4-preparacion/preparar_local.py --forzar --todo                         # rehace todo

--forzar borra los controles y ejecuta la state machine, que rehace lo que quedó sin control.
--estado termina con código 1 si algún control tiene filas distintas entre raw y trusted.
"""
import argparse
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

import pendientes  # noqa: E402


def listar(s3, bucket, prefijo):
    resultado = {}
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefijo):
        for o in pagina.get("Contents", []):
            resultado[o["Key"]] = o["LastModified"]
    return resultado


def estado(s3, bucket):
    lista = pendientes.pendientes(listar(s3, bucket, "raw/"), controles := listar(s3, bucket, pendientes.CONTROL),
                                  R["glue_workers"])
    print(f"Pendientes: {len(lista)}")
    for p in lista:
        print(f"  {p['dataset']:<10} {p['mes']}")
    por_dataset = defaultdict(lambda: {"meses": 0, "raw": 0, "detalle": 0, "viajes": 0, "banderas": defaultdict(int)})
    diferencias = []
    for clave in sorted(controles):
        c = json.loads(s3.get_object(Bucket=bucket, Key=clave)["Body"].read())
        d = por_dataset[c["dataset"]]
        d["meses"] += 1
        d["raw"] += c["filas_raw"]
        d["detalle"] += c["filas_detalle"]
        d["viajes"] += c.get("filas_viajes", 0)
        for b, n in c["banderas"].items():
            d["banderas"][b] += n
        if c["filas_raw"] != c["filas_detalle"] or c.get("filas_viajes", c["filas_raw"]) != c["filas_raw"]:
            diferencias.append(clave)
    print(f"\nControles: {len(controles)}")
    print(f"  {'dataset':<10} {'meses':>5} {'filas raw':>13} {'detalle':>13} {'viajes':>13}")
    for ds, d in sorted(por_dataset.items()):
        print(f"  {ds:<10} {d['meses']:>5} {d['raw']:>13,} {d['detalle']:>13,} {d['viajes']:>13,}")
        for b, n in sorted(d["banderas"].items()):
            print(f"      {b:<22} {n:>13,}  ({n / d['raw']:.2%})")
    if diferencias:
        print(f"\nFilas distintas entre raw y trusted en: {diferencias}")
    return not diferencias


def buscar_state_machine(sfn):
    for pagina in sfn.get_paginator("list_state_machines").paginate():
        for sm in pagina["stateMachines"]:
            if sm["name"] == R["sm_preparacion"]:
                return sm["stateMachineArn"]
    raise SystemExit(f"No existe la state machine {R['sm_preparacion']}. Corre punto4-preparacion/desplegar.py")


def ejecutar(sfn):
    arn = buscar_state_machine(sfn)
    en_curso = sfn.list_executions(stateMachineArn=arn, statusFilter="RUNNING", maxResults=1)["executions"]
    if en_curso:
        print("Ya hay una ejecución en curso; se espera esa.")
        ejecucion_arn = en_curso[0]["executionArn"]
    else:
        ejecucion_arn = sfn.start_execution(stateMachineArn=arn)["executionArn"]
        print(f"Ejecución iniciada: {ejecucion_arn.rsplit(':', 1)[-1]}")
    inicio = time.time()
    while (r := sfn.describe_execution(executionArn=ejecucion_arn))["status"] == "RUNNING":
        print(f"  corriendo... {time.time() - inicio:.0f} s", flush=True)
        time.sleep(30)
    print(f"Estado: {r['status']} en {time.time() - inicio:.0f} s")
    if r["status"] != "SUCCEEDED":
        print(f"Causa: {r.get('cause') or r.get('error') or 'ver el historial en la consola de Step Functions'}")
    return r["status"] == "SUCCEEDED"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--estado", action="store_true")
    g.add_argument("--ejecutar", action="store_true")
    g.add_argument("--forzar", action="store_true")
    p.add_argument("--dataset", choices=sorted(R["glue_workers"]))
    p.add_argument("--mes", help="YYYY-MM (na para taxi_zones)")
    p.add_argument("--todo", action="store_true", help="con --forzar: borra todos los controles")
    args = p.parse_args()
    if args.forzar and not (args.todo or (args.dataset and args.mes)):
        p.error("--forzar necesita --dataset y --mes, o --todo")
    if args.mes and not re.fullmatch(r"\d{4}-\d{2}|na", args.mes):
        p.error("--mes va como YYYY-MM, o na para taxi_zones")

    aws = config.sesion(config.cargar())
    s3, sfn = aws.client("s3"), aws.client("stepfunctions")
    bucket = config.nombre_bucket(aws)
    if args.estado:
        sys.exit(0 if estado(s3, bucket) else 1)
    if args.forzar:
        # Una ejecución en curso ya calculó sus pendientes y podría reescribir el control que se borre ahora.
        if sfn.list_executions(stateMachineArn=buscar_state_machine(sfn), statusFilter="RUNNING",
                               maxResults=1)["executions"]:
            raise SystemExit("Hay una ejecución en curso. Espera a que termine (--ejecutar la espera) y repite.")
        claves = list(listar(s3, bucket, pendientes.CONTROL)) if args.todo else [
            pendientes.clave_control(args.dataset, args.mes)]
        for clave in claves:
            s3.delete_object(Bucket=bucket, Key=clave)
        print(f"Controles borrados: {len(claves)}")
    sys.exit(0 if ejecutar(sfn) else 1)


if __name__ == "__main__":
    main()

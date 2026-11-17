#!/usr/bin/env python3
"""Despliega la catalogación del Punto 5 en AWS Academy. Es idempotente.

  1. Crea el workgroup de Athena tlc-consultas, con resultados en s3://<bucket>/athena/.
  2. Crea o actualiza la Lambda tlc-catalogo (catalogo.py + contrato.py + pendientes.py).
  3. La invoca una vez: base tlc_trusted, las 5 tablas y las particiones de los meses con control.
  4. Vuelve a desplegar el Punto 4, que agrega el paso Catalogar al final de la state machine.

Uso (desde la raíz del repo, después de punto4-preparacion/desplegar.py):
  python punto5-catalogo/desplegar.py
  python punto5-catalogo/desplegar.py --borrar   # Lambda, workgroup y base (trusted/ queda intacto)
"""
import argparse
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from botocore.config import Config

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

CODIGO_LAMBDA = [RAIZ / "punto5-catalogo/catalogo.py", RAIZ / "punto4-preparacion/contrato.py",
                 RAIZ / "punto4-preparacion/pendientes.py"]
DESPLEGAR_P4 = RAIZ / "punto4-preparacion/desplegar.py"


def log(msg):
    print(f"  {msg}", flush=True)


def asegurar_workgroup(athena, bucket):
    nombre = R["athena_workgroup"]
    ajustes = {"ResultConfiguration": {"OutputLocation": f"s3://{bucket}/{R['athena_prefijo']}"},
               "EnforceWorkGroupConfiguration": True, "PublishCloudWatchMetricsEnabled": False}
    try:
        athena.get_work_group(WorkGroup=nombre)  # Athena responde InvalidRequestException si no existe
    except athena.exceptions.InvalidRequestException:
        athena.create_work_group(Name=nombre, Configuration=ajustes, Description="proyecto2-sd Punto 5",
                                 Tags=[{"Key": "Project", "Value": config.PROYECTO}])
        log(f"workgroup de Athena {nombre}: creado")
        return
    athena.update_work_group(WorkGroup=nombre, ConfigurationUpdates={
        "ResultConfigurationUpdates": ajustes["ResultConfiguration"], "EnforceWorkGroupConfiguration": True})
    log(f"workgroup de Athena {nombre}: actualizado")


def zip_lambda():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in CODIGO_LAMBDA:
            z.write(f, f.name)
    return buf.getvalue()


def asegurar_lambda(lam, rol, bucket):
    nombre = R["lambda_catalogo"]
    ajustes = dict(Role=rol, Handler="catalogo.handler", Runtime="python3.12", Timeout=300, MemorySize=256,
                   Environment={"Variables": {"BUCKET": bucket, "BASE": R["glue_base"]}},
                   Description="proyecto2-sd Punto 5: tablas y particiones de trusted en el Glue Data Catalog")
    try:
        lam.get_function(FunctionName=nombre)
        lam.update_function_code(FunctionName=nombre, ZipFile=zip_lambda())
        lam.get_waiter("function_updated_v2").wait(FunctionName=nombre)
        lam.update_function_configuration(FunctionName=nombre, **ajustes)
        lam.get_waiter("function_updated_v2").wait(FunctionName=nombre)
        log(f"Lambda {nombre}: actualizada")
    except lam.exceptions.ResourceNotFoundException:
        lam.create_function(FunctionName=nombre, Code={"ZipFile": zip_lambda()},
                            Tags={"Project": config.PROYECTO}, **ajustes)
        lam.get_waiter("function_active_v2").wait(FunctionName=nombre)
        log(f"Lambda {nombre}: creada")


def invocar(lam):
    r = lam.invoke(FunctionName=R["lambda_catalogo"], Payload=b"{}")
    cuerpo = json.loads(r["Payload"].read())
    if r.get("FunctionError"):
        raise SystemExit(f"La Lambda falló: {cuerpo}")
    log(f"base {R['glue_base']}: {cuerpo['base']}")
    for tabla, t in cuerpo["tablas"].items():
        log(f"  {tabla:<11} tabla {t['tabla']:<11} particiones {t['particiones']:>3} "
            f"({t['particiones_nuevas']} nuevas)")


def borrar(aws):
    lam, athena, glue = aws.client("lambda"), aws.client("athena"), aws.client("glue")
    try:
        lam.delete_function(FunctionName=R["lambda_catalogo"])
        log(f"Lambda {R['lambda_catalogo']}: borrada")
    except lam.exceptions.ResourceNotFoundException:
        log(f"Lambda {R['lambda_catalogo']}: no existía")
    try:
        athena.delete_work_group(WorkGroup=R["athena_workgroup"], RecursiveDeleteOption=True)
        log(f"workgroup {R['athena_workgroup']}: borrado")
    except athena.exceptions.InvalidRequestException:
        log(f"workgroup {R['athena_workgroup']}: no existía")
    try:
        glue.delete_database(Name=R["glue_base"])  # borra también sus tablas; los datos de S3 quedan
        log(f"base {R['glue_base']}: borrada")
    except glue.exceptions.EntityNotFoundException:
        log(f"base {R['glue_base']}: no existía")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--borrar", action="store_true")
    args = p.parse_args()
    aws = config.sesion(config.cargar())
    print("Catalogación (Punto 5)")
    if args.borrar:
        borrar(aws)
    else:
        bucket = config.nombre_bucket(aws)
        rol = f"arn:aws:iam::{aws.client('sts').get_caller_identity()['Account']}:role/LabRole"
        asegurar_workgroup(aws.client("athena"), bucket)
        asegurar_lambda(aws.client("lambda"), rol, bucket)
        # read_timeout por encima del Timeout de la Lambda: si no, botocore corta a los 60 s y reintenta
        invocar(aws.client("lambda", config=Config(read_timeout=330, retries={"max_attempts": 0})))
    print("State machine del Punto 4 (agrega o quita el paso Catalogar)")
    subprocess.run([sys.executable, str(DESPLEGAR_P4), "--solo-state-machine"], check=True)


if __name__ == "__main__":
    main()

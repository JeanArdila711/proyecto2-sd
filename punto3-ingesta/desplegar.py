#!/usr/bin/env python3
"""Despliega la ingesta automática del Punto 3 en AWS Academy. Es idempotente.

  1. Publica el código de la EC2 en s3://<bucket>/codigo/punto3-ingesta/: ec2_ingesta.py, raw.py y,
     del Punto 2, fuente.py y requirements.txt. La Lambda lo baja a la EC2 en cada corrida.
  2. Crea o actualiza la Lambda tlc-ingesta (LabRole, Python 3.12, 15 min, sin reintentos propios:
     la corrida siguiente es el reintento).
  3. Crea o actualiza la regla de EventBridge tlc-ingesta-programada, que la invoca cada 5 minutos.

Requiere la infraestructura del Punto 2 (punto2-fuentes/infra/crear_infra.py).

Uso (desde la raíz del repo):
  python punto3-ingesta/desplegar.py
  python punto3-ingesta/desplegar.py --pausar    # deshabilita la regla; desplegar.py la vuelve a habilitar
  python punto3-ingesta/desplegar.py --borrar    # borra la regla y la Lambda (los datos de raw/ quedan)
"""
import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from botocore.exceptions import ClientError  # noqa: E402

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

DIR = Path(__file__).resolve().parent
DIR_P2 = DIR.parent / "punto2-fuentes" / "ec2"
PREFIJO_CODIGO = R["s3_prefijo_codigo"] + "punto3-ingesta/"
CODIGO_EC2 = [DIR / "ec2_ingesta.py", DIR / "raw.py", DIR_P2 / "fuente.py", DIR_P2 / "requirements.txt"]
CODIGO_LAMBDA = [DIR / "lambda_ingesta.py", DIR / "raw.py"]
ID_DESTINO = "lambda-ingesta"


def log(msg):
    print(f"  {msg}", flush=True)


def publicar_codigo_ec2(s3, bucket):
    for f in CODIGO_EC2:
        s3.upload_file(str(f), bucket, PREFIJO_CODIGO + f.name)
    log(f"código de la EC2 publicado en s3://{bucket}/{PREFIJO_CODIGO} ({len(CODIGO_EC2)} archivos)")


def zip_lambda():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in CODIGO_LAMBDA:
            z.write(f, f.name)
    return buf.getvalue()


def variables(aws, bucket):
    db = aws.client("rds").describe_db_instances(DBInstanceIdentifier=R["rds_id"])["DBInstances"][0]
    if "Endpoint" not in db:
        raise SystemExit(f"La RDS {R['rds_id']} todavía no tiene endpoint ({db['DBInstanceStatus']}). Espera y repite.")
    return {
        "BUCKET": bucket,
        "PARAM_MES": R["param_mes_simulado"],
        "PARAM_PASSWORD": R["param_db_password"],
        "DB_HOST": db["Endpoint"]["Address"],
        "DB_NAME": R["rds_db"],
        "DB_USER": R["rds_usuario"],
        "CARPETA_YELLOW": R["ec2_carpeta_yellow"],
        "DIR_CODIGO": R["ec2_dir_codigo"],
        "PREFIJO_CODIGO": PREFIJO_CODIGO,
        "EC2_NOMBRE": R["ec2_nombre"],
        "PROYECTO": config.PROYECTO,
    }


def asegurar_lambda(lam, rol, entorno):
    nombre = R["lambda_ingesta"]
    ajustes = dict(
        Role=rol,
        Handler="lambda_ingesta.handler",
        Runtime="python3.12",
        Timeout=900,
        MemorySize=2048,
        Environment={"Variables": entorno},
        Description="proyecto2-sd Punto 3: ingesta automática a raw/",
    )
    try:
        lam.get_function(FunctionName=nombre)
        lam.update_function_code(FunctionName=nombre, ZipFile=zip_lambda())
        lam.get_waiter("function_updated_v2").wait(FunctionName=nombre)
        lam.update_function_configuration(FunctionName=nombre, **ajustes)
        lam.get_waiter("function_updated_v2").wait(FunctionName=nombre)
        log(f"Lambda {nombre}: actualizada")
    except lam.exceptions.ResourceNotFoundException:
        lam.create_function(
            FunctionName=nombre, Code={"ZipFile": zip_lambda()}, Tags={"Project": config.PROYECTO}, **ajustes
        )
        lam.get_waiter("function_active_v2").wait(FunctionName=nombre)
        log(f"Lambda {nombre}: creada")
    # Una sola capa de reintentos: EventBridge vuelve a invocar en 5 min; un evento viejo no sirve.
    lam.put_function_event_invoke_config(FunctionName=nombre, MaximumRetryAttempts=0, MaximumEventAgeInSeconds=300)
    try:
        # Una corrida a la vez, para que dos corridas no bajen el mismo mes de HVFHV.
        lam.put_function_concurrency(FunctionName=nombre, ReservedConcurrentExecutions=1)
        log("concurrencia reservada: 1 corrida a la vez")
    except ClientError as e:
        log(f"AVISO: no se pudo reservar concurrencia ({e.response['Error']['Code']}); dos corridas pueden solaparse")
    return lam.get_function(FunctionName=nombre)["Configuration"]["FunctionArn"]


def asegurar_regla(events, lam, arn_lambda):
    regla = events.put_rule(
        Name=R["regla_ingesta"],
        ScheduleExpression=R["ingesta_frecuencia"],
        State="ENABLED",
        Description="proyecto2-sd Punto 3: dispara la ingesta automática",
        Tags=config.etiquetas(),
    )["RuleArn"]
    try:
        lam.add_permission(
            FunctionName=R["lambda_ingesta"],
            StatementId="eventbridge-ingesta",
            Action="lambda:InvokeFunction",
            Principal="events.amazonaws.com",
            SourceArn=regla,
        )
    except lam.exceptions.ResourceConflictException:
        pass  # el permiso ya existía
    events.put_targets(
        Rule=R["regla_ingesta"],
        Targets=[{"Id": ID_DESTINO, "Arn": arn_lambda, "Input": json.dumps({"desde": R["ingesta_desde"]})}],
    )
    log(f"regla {R['regla_ingesta']}: habilitada, {R['ingesta_frecuencia']} -> {R['lambda_ingesta']}")


def borrar(events, lam):
    try:
        events.remove_targets(Rule=R["regla_ingesta"], Ids=[ID_DESTINO])
        events.delete_rule(Name=R["regla_ingesta"])
        log(f"regla {R['regla_ingesta']}: borrada")
    except events.exceptions.ResourceNotFoundException:
        log(f"regla {R['regla_ingesta']}: no existía")
    try:
        lam.delete_function(FunctionName=R["lambda_ingesta"])
        log(f"Lambda {R['lambda_ingesta']}: borrada")
    except lam.exceptions.ResourceNotFoundException:
        log(f"Lambda {R['lambda_ingesta']}: no existía")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--pausar", action="store_true", help="deshabilita la regla de EventBridge")
    g.add_argument("--borrar", action="store_true", help="borra la regla y la Lambda")
    args = p.parse_args()

    aws = config.sesion(config.cargar())
    events, lam = aws.client("events"), aws.client("lambda")
    if args.pausar:
        events.disable_rule(Name=R["regla_ingesta"])
        print(f"regla {R['regla_ingesta']}: deshabilitada. Para reanudar: python punto3-ingesta/desplegar.py")
        return
    if args.borrar:
        borrar(events, lam)
        return

    bucket = config.nombre_bucket(aws)
    cuenta = aws.client("sts").get_caller_identity()["Account"]
    print("Ingesta automática (Punto 3)")
    publicar_codigo_ec2(aws.client("s3"), bucket)
    arn = asegurar_lambda(lam, f"arn:aws:iam::{cuenta}:role/LabRole", variables(aws, bucket))
    asegurar_regla(events, lam, arn)


if __name__ == "__main__":
    main()

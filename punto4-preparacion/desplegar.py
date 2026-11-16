#!/usr/bin/env python3
"""Despliega la preparación raw -> trusted del Punto 4 en AWS Academy. Es idempotente.

  1. Publica preparar.py, contrato.py y pendientes.py en s3://<bucket>/codigo/punto4-preparacion/.
  2. Crea o actualiza el Glue job tlc-preparacion (Glue 5.0, G.1X, LabRole, sin reintentos propios).
  3. Crea o actualiza la Lambda tlc-preparacion-pendientes, que calcula qué falta preparar.
  4. Crea o actualiza la state machine tlc-preparacion: pendientes -> Map -> glue:startJobRun.sync.

Uso (desde la raíz del repo):
  python punto4-preparacion/desplegar.py
  python punto4-preparacion/desplegar.py --borrar    # borra state machine, Lambda y job (trusted/ queda)
"""
import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

DIR = Path(__file__).resolve().parent
PREFIJO_CODIGO = R["s3_prefijo_codigo"] + "punto4-preparacion/"
CODIGO_GLUE = [DIR / "preparar.py", DIR / "contrato.py", DIR / "pendientes.py"]
CODIGO_LAMBDA = [DIR / "lambda_pendientes.py", DIR / "pendientes.py"]
DESCRIPCION = "proyecto2-sd Punto 4: preparación raw -> trusted"


def log(msg):
    print(f"  {msg}", flush=True)


def publicar_codigo(s3, bucket):
    for f in CODIGO_GLUE:
        s3.upload_file(str(f), bucket, PREFIJO_CODIGO + f.name)
    log(f"código del job publicado en s3://{bucket}/{PREFIJO_CODIGO} ({len(CODIGO_GLUE)} archivos)")


def asegurar_job(glue, rol, bucket):
    base = f"s3://{bucket}/{PREFIJO_CODIGO}"
    ajustes = dict(
        Description=DESCRIPCION,
        Role=rol,
        Command={"Name": "glueetl", "ScriptLocation": base + "preparar.py", "PythonVersion": "3"},
        DefaultArguments={
            "--job-language": "python",
            "--bucket": bucket,
            "--extra-py-files": f"{base}contrato.py,{base}pendientes.py",
        },
        ExecutionProperty={"MaxConcurrentRuns": R["preparacion_concurrencia"]},
        MaxRetries=0,  # el reintento es la ejecución siguiente de la state machine
        Timeout=60,
        GlueVersion="5.0",  # fijo: sin GlueVersion queda en 6.0, que no se probó en Academy
        WorkerType="G.1X",
        NumberOfWorkers=2,  # la state machine pasa los workers de cada dataset
    )
    nombre = R["glue_job_preparacion"]
    try:
        glue.get_job(JobName=nombre)
        glue.update_job(JobName=nombre, JobUpdate=ajustes)
        log(f"Glue job {nombre}: actualizado")
    except glue.exceptions.EntityNotFoundException:
        glue.create_job(Name=nombre, Tags={"Project": config.PROYECTO}, **ajustes)
        log(f"Glue job {nombre}: creado")


def zip_lambda():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in CODIGO_LAMBDA:
            z.write(f, f.name)
    return buf.getvalue()


def asegurar_lambda(lam, rol, bucket):
    nombre = R["lambda_pendientes"]
    ajustes = dict(
        Role=rol,
        Handler="lambda_pendientes.handler",
        Runtime="python3.12",
        Timeout=60,
        MemorySize=256,
        Environment={"Variables": {"BUCKET": bucket, "WORKERS": json.dumps(R["glue_workers"])}},
        Description=DESCRIPCION + " (qué falta)",
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
    return lam.get_function(FunctionName=nombre)["Configuration"]["FunctionArn"]


def definicion(arn_lambda):
    job = {
        "Type": "Task",
        "Resource": "arn:aws:states:::glue:startJobRun.sync",
        "Parameters": {
            "JobName": R["glue_job_preparacion"],
            "WorkerType": "G.1X",
            "NumberOfWorkers.$": "$.workers",
            "Arguments": {"--dataset.$": "$.dataset", "--mes.$": "$.mes"},
        },
        # La salida del job se descarta: el item sigue siendo {dataset, mes, workers} (la salida del Map
        # tiene un límite de 256 KiB). El detalle de cada corrida queda en Glue y en el control.
        "ResultPath": None,
        # Glue tarda en liberar el cupo de MaxConcurrentRuns al terminar una corrida (findings.md, fase 0)
        "Retry": [{"ErrorEquals": ["Glue.ConcurrentRunsExceededException"], "IntervalSeconds": 30,
                   "MaxAttempts": 6, "BackoffRate": 1.5}],
        # Un mes que falla no frena a los demás: se anota el error y se sigue; al final, Fallidos decide.
        "Catch": [{"ErrorEquals": ["States.ALL"], "ResultPath": "$.error", "Next": "Anotar falla"}],
        "End": True,
    }
    return {
        "Comment": DESCRIPCION,
        "StartAt": "Pendientes",
        "States": {
            "Pendientes": {
                "Type": "Task",
                "Resource": "arn:aws:states:::lambda:invoke",
                "Parameters": {"FunctionName": arn_lambda, "Payload": {}},
                "OutputPath": "$.Payload",
                "Next": "Procesar",
            },
            "Procesar": {
                "Type": "Map",
                "ItemsPath": "$.pendientes",
                "MaxConcurrency": R["preparacion_concurrencia"],
                "ItemProcessor": {
                    "ProcessorConfig": {"Mode": "INLINE"},
                    "StartAt": "Job",
                    "States": {"Job": job, "Anotar falla": {"Type": "Pass", "End": True}},
                },
                "Next": "Fallidos",
            },
            "Fallidos": {"Type": "Pass", "Parameters": {"fallidos.$": "$[?(@.error)]"}, "Next": "Hubo fallas"},
            "Hubo fallas": {
                "Type": "Choice",
                "Choices": [{"Variable": "$.fallidos[0]", "IsPresent": True, "Next": "Fallo"}],
                "Default": "Listo",
            },
            "Fallo": {"Type": "Fail", "Error": "MesesFallidos", "Cause": "Algún mes falló; ver el Map"},
            "Listo": {"Type": "Succeed"},
        },
    }


def buscar_state_machine(sfn):
    for pagina in sfn.get_paginator("list_state_machines").paginate():
        for sm in pagina["stateMachines"]:
            if sm["name"] == R["sm_preparacion"]:
                return sm["stateMachineArn"]
    return None


def asegurar_state_machine(sfn, rol, arn_lambda):
    cuerpo = json.dumps(definicion(arn_lambda))
    arn = buscar_state_machine(sfn)
    if arn:
        sfn.update_state_machine(stateMachineArn=arn, definition=cuerpo, roleArn=rol)
        log(f"state machine {R['sm_preparacion']}: actualizada")
    else:
        sfn.create_state_machine(
            name=R["sm_preparacion"], definition=cuerpo, roleArn=rol, type="STANDARD",
            tags=[{"key": "Project", "value": config.PROYECTO}],
        )
        log(f"state machine {R['sm_preparacion']}: creada")


def borrar(glue, lam, sfn):
    arn = buscar_state_machine(sfn)
    if arn:
        sfn.delete_state_machine(stateMachineArn=arn)
        log(f"state machine {R['sm_preparacion']}: borrada")
    else:
        log(f"state machine {R['sm_preparacion']}: no existía")
    try:
        lam.delete_function(FunctionName=R["lambda_pendientes"])
        log(f"Lambda {R['lambda_pendientes']}: borrada")
    except lam.exceptions.ResourceNotFoundException:
        log(f"Lambda {R['lambda_pendientes']}: no existía")
    glue.delete_job(JobName=R["glue_job_preparacion"])  # no falla si no existe
    log(f"Glue job {R['glue_job_preparacion']}: borrado (o no existía)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--borrar", action="store_true", help="borra la state machine, la Lambda y el job")
    args = p.parse_args()

    aws = config.sesion(config.cargar())
    glue, lam, sfn = aws.client("glue"), aws.client("lambda"), aws.client("stepfunctions")
    if args.borrar:
        borrar(glue, lam, sfn)
        return

    bucket = config.nombre_bucket(aws)
    cuenta = aws.client("sts").get_caller_identity()["Account"]
    rol = f"arn:aws:iam::{cuenta}:role/LabRole"
    print("Preparación raw -> trusted (Punto 4)")
    publicar_codigo(aws.client("s3"), bucket)
    asegurar_job(glue, rol, bucket)
    arn_lambda = asegurar_lambda(lam, rol, bucket)
    asegurar_state_machine(sfn, rol, arn_lambda)


if __name__ == "__main__":
    main()

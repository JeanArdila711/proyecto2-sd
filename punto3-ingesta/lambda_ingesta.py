"""Lambda tlc-ingesta: ingesta automática del Punto 3. La dispara EventBridge cada pocos minutos.

En cada corrida:
  1. Lanza por SSM la ingesta de la EC2 (ec2_ingesta.py: yellow desde archivos, green y taxi_zones
     desde MariaDB). Si la EC2 está apagada, la omite.
  2. HVFHV desde la URL de la TLC: descarga por streaming a S3 cada mes entre event["desde"] y el
     reloj simulado (Parameter Store) que todavía no esté en raw/. Para antes de quedarse sin tiempo;
     lo que falte lo trae la corrida siguiente.
  3. Espera el resultado de la EC2 y devuelve un resumen. Si algo falló, termina con error.

Evento: {"desde": "2024-01"} (obligatorio; lo pone la regla de EventBridge o ingestar.py).
Variables de entorno: las pone desplegar.py.
"""
import http.client
import json
import os
import time
import urllib.request

import boto3
from boto3.exceptions import S3UploadFailedError
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

import raw

URL_TLC = "https://d37ci6vzurychx.cloudfront.net/trip-data"
MARGEN_MS = 180_000  # no empezar un archivo de HVFHV (hasta 511 MiB) con menos de 3 min por delante
TRANSFERENCIA = TransferConfig(multipart_chunksize=16 * 2**20, max_concurrency=8)

s3 = boto3.client("s3")
ssm = boto3.client("ssm")
ec2 = boto3.client("ec2")


def env(nombre):
    return os.environ[nombre]


def objetos(bucket, prefijo):
    """{clave: tamaño} de todo lo que hay bajo el prefijo."""
    resultado = {}
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefijo):
        for o in pagina.get("Contents", []):
            resultado[o["Key"]] = o["Size"]
    return resultado


# ------------------------------------------------------------------ HVFHV desde la URL
def mes_simulado():
    try:
        return ssm.get_parameter(Name=env("PARAM_MES"))["Parameter"]["Value"]
    except ssm.exceptions.ParameterNotFound:
        return None


def subir_hvfhv(bucket, mes):
    """Copia fhvhv_tripdata_<mes>.parquet de la TLC a raw/ sin pasar por disco. Devuelve MiB y segundos."""
    archivo = f"fhvhv_tripdata_{mes}.parquet"
    clave = raw.clave("hvfhv", mes, archivo)
    inicio = time.time()
    with urllib.request.urlopen(f"{URL_TLC}/{archivo}", timeout=60) as r:
        esperado = int(r.headers["Content-Length"])
        # La subida multiparte solo aparece en S3 al completarse: nadie ve un archivo a medias.
        s3.upload_fileobj(r, bucket, clave, Config=TRANSFERENCIA)
    subido = s3.head_object(Bucket=bucket, Key=clave)["ContentLength"]
    if subido != esperado:
        s3.delete_object(Bucket=bucket, Key=clave)
        raise RuntimeError(f"{archivo}: se subieron {subido} bytes de {esperado}; se borró")
    return esperado / 2**20, time.time() - inicio


def ingerir_hvfhv(bucket, desde, context, resumen):
    hasta = mes_simulado()
    if not hasta:
        resumen["hvfhv"].append("reloj simulado vacío: no hay meses de HVFHV liberados")
        return
    existentes = objetos(bucket, raw.PREFIJO + "hvfhv/")
    faltan = [m for m in raw.meses(desde, hasta) if raw.clave("hvfhv", m, f"fhvhv_tripdata_{m}.parquet") not in existentes]
    resumen["hvfhv"].append(f"liberados {desde} .. {hasta}; faltan en raw: {len(faltan)}")
    for mes in faltan:
        if context.get_remaining_time_in_millis() < MARGEN_MS:
            resumen["hvfhv"].append(f"sin tiempo: quedan {len(faltan) - faltan.index(mes)} meses para la próxima corrida")
            return
        try:
            mib, seg = subir_hvfhv(bucket, mes)
            resumen["hvfhv"].append(f"{mes}: {mib:.0f} MiB en {seg:.0f} s")
        # OSError cubre URLError/HTTPError y los timeouts del socket; HTTPException, una descarga cortada
        except (OSError, http.client.HTTPException, ClientError, S3UploadFailedError, RuntimeError) as e:
            resumen["errores"].append(f"hvfhv {mes}: {e}")


# ------------------------------------------------------------------ EC2: yellow, green y zonas
def comandos_ec2():
    base = env("DIR_CODIGO")
    destino = f"{base}/punto3-ingesta"
    py = f"{base}/venv/bin/python"
    return [
        "set -eu",
        f"export AWS_DEFAULT_REGION={env('AWS_REGION')} TLC_BUCKET={env('BUCKET')}",
        f"export TLC_DB_HOST={env('DB_HOST')} TLC_DB_NAME={env('DB_NAME')} TLC_DB_USER={env('DB_USER')}",
        f"export TLC_PARAM_PASSWORD={env('PARAM_PASSWORD')} TLC_CARPETA_YELLOW={env('CARPETA_YELLOW')}",
        f"mkdir -p {destino}",
        f"aws s3 sync s3://{env('BUCKET')}/{env('PREFIJO_CODIGO')} {destino}/ --delete --only-show-errors",
        # Mismo entorno que el Punto 2 (punto2-fuentes/remoto.py): Python 3.11 en un venv
        "command -v python3.11 > /dev/null || dnf install -y -q python3.11",
        f"[ -x {base}/venv/bin/python3.11 ] || (rm -rf {base}/venv && python3.11 -m venv {base}/venv)",
        f"{base}/venv/bin/pip install -q --disable-pip-version-check -r {destino}/requirements.txt",
        f"cd {destino}",
        # Una sola ingesta de la EC2 a la vez: si la anterior sigue corriendo, esta se omite
        "rc=0; flock -n -E 99 /tmp/tlc-ingesta.lock " + py + " -u ec2_ingesta.py || rc=$?",
        'if [ "$rc" -eq 99 ]; then echo "otra ingesta de la EC2 sigue en curso; se omite"; exit 0; fi',
        'exit "$rc"',
    ]


def lanzar_ec2():
    reservas = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [env("EC2_NOMBRE")]},
            {"Name": "tag:Project", "Values": [env("PROYECTO")]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]
    )["Reservations"]
    ids = [i["InstanceId"] for r in reservas for i in r["Instances"]]
    if not ids:
        return None, None
    cid = ssm.send_command(
        InstanceIds=ids[:1],
        DocumentName="AWS-RunShellScript",
        Comment="proyecto2-sd: ingesta de la EC2 (Punto 3)",
        Parameters={"commands": comandos_ec2(), "executionTimeout": ["3600"]},
        TimeoutSeconds=600,
    )["Command"]["CommandId"]
    return ids[0], cid


def esperar_ec2(instancia, cid, context, resumen):
    if not cid:
        resumen["ec2"] = "omitida: la EC2 no está corriendo"
        return
    while context.get_remaining_time_in_millis() > 20_000:
        try:
            r = ssm.get_command_invocation(CommandId=cid, InstanceId=instancia)
        except ssm.exceptions.InvocationDoesNotExist:
            r = {"Status": "Pending"}
        if r["Status"] not in ("Pending", "InProgress", "Delayed"):
            resumen["ec2"] = f"{r['Status']} (SSM {cid})\n{r['StandardOutputContent'].rstrip()[-3000:]}"
            if r["Status"] != "Success":
                resumen["errores"].append(f"ec2: {r['Status']}: {r['StandardErrorContent'].rstrip()[-1000:]}")
            return
        time.sleep(5)
    resumen["ec2"] = f"sigue corriendo (SSM {cid}); el resultado queda en el historial de Run Command"


def handler(event, context):
    desde = event["desde"]
    bucket = env("BUCKET")
    resumen = {"hvfhv": [], "ec2": "", "errores": []}
    try:
        instancia, cid = lanzar_ec2()
    except ClientError as e:  # que una falla de la EC2 no frene HVFHV
        instancia = cid = False
        resumen["ec2"] = "no se pudo lanzar"
        resumen["errores"].append(f"ec2: no se pudo lanzar: {e}")
    ingerir_hvfhv(bucket, desde, context, resumen)
    if cid is not False:
        esperar_ec2(instancia, cid, context, resumen)
    print(json.dumps(resumen, ensure_ascii=False))
    if resumen["errores"]:
        raise RuntimeError(json.dumps(resumen, ensure_ascii=False))
    return resumen

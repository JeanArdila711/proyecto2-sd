"""Ejecuta los scripts de punto2-fuentes/ec2/ dentro de la EC2 de archivos, por Session Manager.

La RDS es privada, así que todo lo que habla con MariaDB corre en la EC2. Desde el portátil:
  1. se sube punto2-fuentes/ec2/ a s3://<bucket>/codigo/punto2-fuentes/ec2/
  2. por SSM, la EC2 lo descarga, prepara su entorno de Python (/opt/proyecto2/venv) y corre el script
  3. se espera el resultado y se imprime la salida
"""
import shlex
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

DIR_EC2 = Path(__file__).resolve().parent / "ec2"
PREFIJO = R["s3_prefijo_codigo"] + "punto2-fuentes/ec2/"


def instancia_fuente(aws):
    reservas = aws.client("ec2").describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [R["ec2_nombre"]]},
            {"Name": "tag:Project", "Values": [config.PROYECTO]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]
    )["Reservations"]
    ids = [i["InstanceId"] for r in reservas for i in r["Instances"]]
    if not ids:
        raise SystemExit(f"La EC2 {R['ec2_nombre']} no está corriendo. Corre primero infra/crear_infra.py.")
    return ids[0]


def host_rds(aws):
    db = aws.client("rds").describe_db_instances(DBInstanceIdentifier=R["rds_id"])["DBInstances"][0]
    if db["DBInstanceStatus"] != "available":
        raise SystemExit(f"La RDS {R['rds_id']} está '{db['DBInstanceStatus']}'. Corre infra/crear_infra.py.")
    return db["Endpoint"]["Address"]


def publicar_codigo(aws, bucket):
    s3 = aws.client("s3")
    archivos = [f for f in DIR_EC2.iterdir() if f.is_file() and f.suffix in (".py", ".sql", ".txt")]
    for f in archivos:
        s3.upload_file(str(f), bucket, PREFIJO + f.name)
    print(f"código publicado en s3://{bucket}/{PREFIJO} ({len(archivos)} archivos)")


def correr_en_ec2(script, argumentos=(), timeout=3600):
    """Publica el código y corre `script` (de punto2-fuentes/ec2/) en la EC2. Devuelve la salida."""
    cfg = config.cargar()
    aws = config.sesion(cfg)
    bucket = config.nombre_bucket(aws)
    instancia = instancia_fuente(aws)
    host = host_rds(aws)
    publicar_codigo(aws, bucket)

    base = R["ec2_dir_codigo"]
    destino = f"{base}/punto2-fuentes/ec2"
    comandos = [
        "set -eu",
        f"export AWS_DEFAULT_REGION={aws.region_name}",
        f"export TLC_DB_HOST={host} TLC_DB_NAME={R['rds_db']} TLC_DB_USER={R['rds_usuario']}",
        f"export TLC_PARAM_PASSWORD={R['param_db_password']} TLC_PARAM_MES={R['param_mes_simulado']}",
        f"export TLC_CARPETA_YELLOW={R['ec2_carpeta_yellow']}",
        f"mkdir -p {destino}",
        f"aws s3 sync s3://{bucket}/{PREFIJO} {destino}/ --delete --only-show-errors",
        # Python 3.11 de Amazon Linux 2023 (el python3 del sistema es 3.9, sin soporte de boto3)
        "command -v python3.11 > /dev/null || dnf install -y -q python3.11",
        f"[ -x {base}/venv/bin/python3.11 ] || (rm -rf {base}/venv && python3.11 -m venv {base}/venv)",
        f"{base}/venv/bin/pip install -q --disable-pip-version-check -r {destino}/requirements.txt",
        f"cd {destino}",
        f"{base}/venv/bin/python -u {shlex.quote(script)} {' '.join(shlex.quote(a) for a in argumentos)}",
        "chown -R ec2-user:ec2-user /data",
    ]
    ssm = aws.client("ssm")
    cid = ssm.send_command(
        InstanceIds=[instancia],
        DocumentName="AWS-RunShellScript",
        Comment=f"proyecto2-sd: {script}"[:100],
        Parameters={"commands": comandos, "executionTimeout": [str(timeout)]},
        TimeoutSeconds=600,
    )["Command"]["CommandId"]
    print(f"corriendo {script} en {instancia} (SSM {cid})", end="", flush=True)

    inicio = time.time()
    while True:
        time.sleep(5)
        try:
            r = ssm.get_command_invocation(CommandId=cid, InstanceId=instancia)
        except ssm.exceptions.InvocationDoesNotExist:
            continue
        if r["Status"] not in ("Pending", "InProgress", "Delayed"):
            break
        print(".", end="", flush=True)
    print(f" {r['Status']} ({time.time() - inicio:.0f} s)\n")
    print(r["StandardOutputContent"].rstrip())
    if r["Status"] != "Success":
        print(r["StandardErrorContent"].rstrip(), file=sys.stderr)
        raise SystemExit(1)
    return r["StandardOutputContent"]

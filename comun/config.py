"""Configuración compartida por todos los scripts del proyecto.

Lee `config.env` en la raíz del repo y define los nombres de los recursos de AWS,
para que cada punto encuentre lo que creó el anterior sin archivos de estado.
"""
import hashlib
from pathlib import Path

import boto3

RAIZ = Path(__file__).resolve().parents[1]
ARCHIVO_CONFIG = RAIZ / "config.env"

PROYECTO = "proyecto2-sd"
ETIQUETAS = [{"Key": "Project", "Value": PROYECTO}]

# Nombres de los recursos. El bucket se completa con un sufijo derivado de la cuenta
# (ver nombre_bucket) porque los nombres de bucket son globales.
RECURSOS = {
    "sg_ec2": "tlc-ec2-sg",
    "sg_rds": "tlc-rds-sg",
    "db_subnet_group": "tlc-db-subnets",
    "rds_id": "tlc-mariadb",
    "rds_db": "tlc",
    "rds_usuario": "tlcadmin",
    "rds_clase": "db.t3.micro",
    "rds_version": "11.8",  # rama LTS de MariaDB; se usa el último parche disponible
    "ec2_nombre": "tlc-fuente-archivos",
    "ec2_tipo": "t3.small",
    "ec2_perfil": "LabInstanceProfile",
    "ec2_llave": "vockey",
    "ec2_carpeta_yellow": "/data/tlc/yellow",
    "ec2_dir_codigo": "/opt/proyecto2",
    # Parameter Store: contraseña de MariaDB (SecureString) y reloj del simulador (último mes liberado)
    "param_db_password": "/proyecto2-sd/db/password",
    "param_mes_simulado": "/proyecto2-sd/simulacion/mes_actual",
    # Prefijo del bucket donde se publica el código que corre en la EC2 (fuera de las zonas del datalake)
    "s3_prefijo_codigo": "codigo/",
    # Punto 3: ingesta automática
    "lambda_ingesta": "tlc-ingesta",
    "regla_ingesta": "tlc-ingesta-programada",
    "ingesta_frecuencia": "rate(5 minutes)",
    "ingesta_desde": "2024-01",  # primer mes del alcance de datos (convención "Alcance de datos")
    # Punto 4: preparación raw -> trusted
    "glue_job_preparacion": "tlc-preparacion",
    "lambda_pendientes": "tlc-preparacion-pendientes",
    "sm_preparacion": "tlc-preparacion",
    "trusted_prefijo": "trusted/",
    "control_prefijo": "trusted/_control/",
    # Workers G.1X por dataset (mínimo de Glue Spark: 2). Todos en 2 mientras no se conozcan los límites de
    # Glue de Vocareum: 2 workers y un job a la vez es lo único que corrió sin desactivar la cuenta (findings.md).
    "glue_workers": {"taxi_zones": 2, "green": 2, "yellow": 2, "hvfhv": 2},
    # 1: varios jobs de Glue a la vez desactivaron la cuenta de Academy (findings.md, 2026-11-15)
    "preparacion_concurrencia": 1,  # MaxConcurrency del Map y MaxConcurrentRuns del job
    # Punto 5: catalogación (Glue Data Catalog, Athena y EMR/Hive)
    "glue_base": "tlc_trusted",
    "lambda_catalogo": "tlc-catalogo",  # último paso de la state machine tlc-preparacion
    "athena_workgroup": "tlc-consultas",
    "athena_prefijo": "athena/",  # resultados de Athena, fuera de raw/ y trusted/
}

URL_TLC = "https://d37ci6vzurychx.cloudfront.net"


def cargar():
    """Devuelve config.env como dict. Falla con un mensaje claro si no existe."""
    if not ARCHIVO_CONFIG.exists():
        raise SystemExit(
            f"No existe {ARCHIVO_CONFIG.name}. Créalo con: cp config.example.env config.env"
        )
    cfg = {}
    for linea in ARCHIVO_CONFIG.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        cfg[clave.strip()] = valor.split(" #", 1)[0].strip()
    return cfg


def guardar_valor(clave, valor):
    """Escribe o reemplaza CLAVE=valor en config.env."""
    lineas = ARCHIVO_CONFIG.read_text(encoding="utf-8").splitlines()
    for i, linea in enumerate(lineas):
        if linea.strip().startswith(f"{clave}="):
            lineas[i] = f"{clave}={valor}"
            break
    else:
        lineas.append(f"{clave}={valor}")
    ARCHIVO_CONFIG.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def sesion(cfg):
    return boto3.Session(
        profile_name=cfg.get("AWS_PROFILE") or None,
        region_name=cfg.get("AWS_REGION") or "us-east-1",
    )


def nombre_bucket(sesion_aws):
    """proyecto2-tlc-<8 hex>: único por cuenta y estable entre corridas, sin exponer el ID."""
    cuenta = sesion_aws.client("sts").get_caller_identity()["Account"]
    return "proyecto2-tlc-" + hashlib.sha256(cuenta.encode()).hexdigest()[:8]


def etiquetas(nombre=None):
    tags = list(ETIQUETAS)
    if nombre:
        tags.append({"Key": "Name", "Value": nombre})
    return tags

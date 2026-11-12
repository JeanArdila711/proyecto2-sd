#!/usr/bin/env python3
"""Detiene la EC2 y la RDS del Punto 2 sin borrar nada, para no gastar presupuesto entre sesiones.

Los datos se conservan (disco de la EC2 y almacenamiento de la RDS). Para volver a encenderlas:
  python punto2-fuentes/infra/crear_infra.py

Ojo: AWS vuelve a encender sola una RDS detenida a los 7 días.

Uso (desde la raíz del repo):
  python punto2-fuentes/infra/apagar_infra.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from botocore.exceptions import ClientError  # noqa: E402

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402


def main():
    cfg = config.cargar()
    aws = config.sesion(cfg)
    ec2, rds = aws.client("ec2"), aws.client("rds")

    reservas = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [R["ec2_nombre"]]},
            {"Name": "tag:Project", "Values": [config.PROYECTO]},
            {"Name": "instance-state-name", "Values": ["pending", "running"]},
        ]
    )["Reservations"]
    ids = [i["InstanceId"] for r in reservas for i in r["Instances"]]
    if ids:
        ec2.stop_instances(InstanceIds=ids)
        print(f"EC2 deteniéndose: {', '.join(ids)}")
    else:
        print("EC2: no hay ninguna corriendo")

    try:
        rds.stop_db_instance(DBInstanceIdentifier=R["rds_id"])
        print(f"RDS {R['rds_id']}: deteniéndose")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("InvalidDBInstanceState", "DBInstanceNotFound"):
            print(f"RDS {R['rds_id']}: {e.response['Error']['Message']}")
        else:
            raise


if __name__ == "__main__":
    main()

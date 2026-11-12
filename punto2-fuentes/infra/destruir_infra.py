#!/usr/bin/env python3
"""Borra la infraestructura que crea crear_infra.py, para no gastar presupuesto del laboratorio.

Borra la EC2, la RDS (sin snapshot final), el DB subnet group, los security groups, el endpoint
de S3 y los parámetros /proyecto2-sd/* de Parameter Store. El bucket del datalake solo se borra con --incluir-bucket, porque contiene los datos.

Uso (desde la raíz del repo):
  python punto2-fuentes/infra/destruir_infra.py --confirmar
  python punto2-fuentes/infra/destruir_infra.py --confirmar --incluir-bucket
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from botocore.exceptions import ClientError  # noqa: E402

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402


def log(msg):
    print(f"  {msg}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirmar", action="store_true", help="obligatorio: confirma que se borra todo")
    parser.add_argument("--incluir-bucket", action="store_true", help="vacía y borra también el bucket del datalake")
    args = parser.parse_args()
    if not args.confirmar:
        raise SystemExit("No se borró nada. Agrega --confirmar para borrar la infraestructura.")

    cfg = config.cargar()
    aws = config.sesion(cfg)
    ec2, rds = aws.client("ec2"), aws.client("rds")

    # EC2: solo la del proyecto (Name + Project)
    reservas = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [R["ec2_nombre"]]},
            {"Name": "tag:Project", "Values": [config.PROYECTO]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
    )["Reservations"]
    ids = [i["InstanceId"] for r in reservas for i in r["Instances"]]
    if ids:
        ec2.terminate_instances(InstanceIds=ids)
        log(f"EC2 terminándose: {', '.join(ids)}")

    # RDS
    try:
        rds.delete_db_instance(
            DBInstanceIdentifier=R["rds_id"], SkipFinalSnapshot=True, DeleteAutomatedBackups=True
        )
        log(f"RDS {R['rds_id']}: borrándose (~5-10 min)")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "DBInstanceNotFound":
            log(f"RDS {R['rds_id']}: no existe")
        elif code == "InvalidDBInstanceState":
            log(f"RDS {R['rds_id']}: ya se está borrando")
        else:
            raise

    if ids:
        ec2.get_waiter("instance_terminated").wait(InstanceIds=ids)
        log("EC2 terminada")
    try:
        rds.get_waiter("db_instance_deleted").wait(
            DBInstanceIdentifier=R["rds_id"], WaiterConfig={"Delay": 30, "MaxAttempts": 60}
        )
        log("RDS borrada")
    except ClientError:
        pass

    try:
        rds.delete_db_subnet_group(DBSubnetGroupName=R["db_subnet_group"])
        log(f"DB subnet group {R['db_subnet_group']}: borrado")
    except ClientError as e:
        if e.response["Error"]["Code"] != "DBSubnetGroupNotFoundFault":
            raise

    # Endpoint de S3 creado por el proyecto
    eps = ec2.describe_vpc_endpoints(Filters=[{"Name": "tag:Project", "Values": [config.PROYECTO]}])["VpcEndpoints"]
    vivos = [e["VpcEndpointId"] for e in eps if e["State"].lower() not in ("deleted", "deleting")]
    if vivos:
        ec2.delete_vpc_endpoints(VpcEndpointIds=vivos)
        log(f"endpoint de S3 borrado: {', '.join(vivos)}")

    # Security groups: primero quitar la referencia cruzada, luego borrar (reintenta mientras se liberan las ENIs)
    sgs = ec2.describe_security_groups(
        Filters=[{"Name": "group-name", "Values": [R["sg_ec2"], R["sg_rds"]]},
                 {"Name": "tag:Project", "Values": [config.PROYECTO]}]
    )["SecurityGroups"]
    for sg in sgs:
        if sg["IpPermissions"]:
            ec2.revoke_security_group_ingress(GroupId=sg["GroupId"], IpPermissions=sg["IpPermissions"])
    for sg in sgs:
        for intento in range(20):
            try:
                ec2.delete_security_group(GroupId=sg["GroupId"])
                log(f"security group {sg['GroupName']}: borrado")
                break
            except ClientError as e:
                if e.response["Error"]["Code"] != "DependencyViolation" or intento == 19:
                    raise
                time.sleep(15)

    # Parámetros de Parameter Store (contraseña y reloj del simulador)
    params = [R["param_db_password"], R["param_mes_simulado"]]
    borrados = aws.client("ssm").delete_parameters(Names=params)["DeletedParameters"]
    if borrados:
        log(f"parámetros borrados: {', '.join(borrados)}")

    if args.incluir_bucket:
        bucket = config.nombre_bucket(aws)
        b = aws.resource("s3").Bucket(bucket)
        try:
            b.objects.all().delete()
            b.delete()
            log(f"bucket {bucket}: vaciado y borrado")
        except ClientError as e:
            if e.response["Error"]["Code"] != "NoSuchBucket":
                raise
    print("Listo.")


if __name__ == "__main__":
    main()

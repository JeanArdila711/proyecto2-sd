#!/usr/bin/env python3
"""Crea la infraestructura de las fuentes de datos (Punto 2) en AWS Academy.

Recursos (todos con la etiqueta Project=proyecto2-sd):
  - Bucket S3 del datalake: proyecto2-tlc-<sufijo>, privado.
  - Security groups: tlc-ec2-sg (SSH) y tlc-rds-sg (MariaDB desde la EC2 y desde sí mismo,
    esto último para la conexión JDBC de Glue del Punto 3).
  - Endpoint gateway de S3 en la VPC por defecto (Glue dentro de la VPC lo necesita para llegar a S3).
  - RDS MariaDB tlc-mariadb (db.t3.micro, 20 GB, privada).
  - EC2 tlc-fuente-archivos (t3.small, Amazon Linux 2023, LabInstanceProfile) con la carpeta
    /data/tlc/yellow para los archivos de taxis amarillos.

Es idempotente: si un recurso ya existe lo reutiliza, y si la EC2 o la RDS están detenidas las arranca.

Uso (desde la raíz del repo):
  python punto2-fuentes/infra/crear_infra.py            # crea y espera a que todo esté disponible
  python punto2-fuentes/infra/crear_infra.py --no-esperar
"""
import argparse
import secrets
import ssl
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from botocore.exceptions import ClientError  # noqa: E402
from botocore.httpsession import get_cert_path  # noqa: E402

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

USER_DATA = f"""#!/bin/bash
set -euxo pipefail
dnf install -y python3-pip mariadb105
mkdir -p {R["ec2_carpeta_yellow"]}
chown -R ec2-user:ec2-user /data
"""

AMI_PARAM = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"


def log(msg):
    print(f"  {msg}", flush=True)


def codigo(e):
    return e.response["Error"]["Code"]


# ---------------------------------------------------------------- S3
def asegurar_bucket(s3, nombre):
    try:
        s3.head_bucket(Bucket=nombre)
        log(f"bucket {nombre}: ya existe")
    except ClientError as e:
        if codigo(e) in ("403", "Forbidden"):
            raise SystemExit(f"El bucket {nombre} existe pero es de otra cuenta.")
        s3.create_bucket(Bucket=nombre)  # us-east-1 no lleva LocationConstraint
        log(f"bucket {nombre}: creado")
    s3.put_public_access_block(
        Bucket=nombre,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_tagging(Bucket=nombre, Tagging={"TagSet": config.ETIQUETAS})


# ---------------------------------------------------------------- Red
def vpc_por_defecto(ec2):
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "is-default", "Values": ["true"]}])["Vpcs"]
    if not vpcs:
        raise SystemExit("La cuenta no tiene VPC por defecto.")
    return vpcs[0]["VpcId"]


def asegurar_sg(ec2, vpc, nombre, descripcion):
    existentes = ec2.describe_security_groups(
        Filters=[{"Name": "vpc-id", "Values": [vpc]}, {"Name": "group-name", "Values": [nombre]}]
    )["SecurityGroups"]
    if existentes:
        log(f"security group {nombre}: ya existe")
        return existentes[0]["GroupId"]
    sg = ec2.create_security_group(
        GroupName=nombre,
        Description=descripcion,
        VpcId=vpc,
        TagSpecifications=[{"ResourceType": "security-group", "Tags": config.etiquetas(nombre)}],
    )["GroupId"]
    log(f"security group {nombre}: creado")
    return sg


def permitir(ec2, sg, permiso):
    try:
        ec2.authorize_security_group_ingress(GroupId=sg, IpPermissions=[permiso])
    except ClientError as e:
        if codigo(e) != "InvalidPermission.Duplicate":
            raise


def ip_publica():
    # Certificados de botocore: el Python de python.org en macOS no trae los del sistema.
    ctx = ssl.create_default_context(cafile=get_cert_path(True))
    with urllib.request.urlopen("https://checkip.amazonaws.com", timeout=10, context=ctx) as r:
        return r.read().decode().strip() + "/32"


def asegurar_endpoint_s3(ec2, vpc, region):
    servicio = f"com.amazonaws.{region}.s3"
    existentes = [
        e
        for e in ec2.describe_vpc_endpoints(
            Filters=[{"Name": "vpc-id", "Values": [vpc]}, {"Name": "service-name", "Values": [servicio]}]
        )["VpcEndpoints"]
        if e["State"].lower() not in ("deleted", "deleting")
    ]
    if existentes:
        log("endpoint gateway de S3: ya existe")
        return
    tablas = [
        t["RouteTableId"]
        for t in ec2.describe_route_tables(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["RouteTables"]
    ]
    ec2.create_vpc_endpoint(
        VpcEndpointType="Gateway",
        VpcId=vpc,
        ServiceName=servicio,
        RouteTableIds=tablas,
        TagSpecifications=[{"ResourceType": "vpc-endpoint", "Tags": config.etiquetas("tlc-s3-endpoint")}],
    )
    log("endpoint gateway de S3: creado")


# ---------------------------------------------------------------- RDS
def asegurar_subnet_group(rds, ec2, vpc):
    nombre = R["db_subnet_group"]
    try:
        rds.describe_db_subnet_groups(DBSubnetGroupName=nombre)
        log(f"DB subnet group {nombre}: ya existe")
        return
    except ClientError as e:
        if codigo(e) != "DBSubnetGroupNotFoundFault":
            raise
    subredes = [
        s["SubnetId"]
        for s in ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]}])["Subnets"]
    ]
    rds.create_db_subnet_group(
        DBSubnetGroupName=nombre,
        DBSubnetGroupDescription="Subredes de la VPC por defecto para tlc-mariadb",
        SubnetIds=subredes,
        Tags=config.ETIQUETAS,
    )
    log(f"DB subnet group {nombre}: creado")


def version_mariadb(rds, rama):
    versiones = [
        v["EngineVersion"]
        for v in rds.describe_db_engine_versions(Engine="mariadb")["DBEngineVersions"]
        if v["EngineVersion"].startswith(rama + ".")
    ]
    if not versiones:
        raise SystemExit(f"RDS no ofrece MariaDB {rama}.x en esta región.")
    return max(versiones, key=lambda v: [int(x) for x in v.split(".")])


def asegurar_rds(rds, cfg, sg_rds):
    ident = R["rds_id"]
    try:
        db = rds.describe_db_instances(DBInstanceIdentifier=ident)["DBInstances"][0]
        estado = db["DBInstanceStatus"]
        log(f"RDS {ident}: ya existe ({estado})")
        if estado == "stopped":
            rds.start_db_instance(DBInstanceIdentifier=ident)
            log(f"RDS {ident}: arrancando")
        return
    except ClientError as e:
        if codigo(e) != "DBInstanceNotFound":
            raise

    password = cfg.get("DB_PASSWORD")
    if not password:
        password = secrets.token_urlsafe(18)
        config.guardar_valor("DB_PASSWORD", password)
        log("DB_PASSWORD generada y guardada en config.env")

    version = version_mariadb(rds, R["rds_version"])
    rds.create_db_instance(
        DBInstanceIdentifier=ident,
        DBName=R["rds_db"],
        Engine="mariadb",
        EngineVersion=version,
        DBInstanceClass=R["rds_clase"],
        AllocatedStorage=20,
        StorageType="gp3",
        MasterUsername=R["rds_usuario"],
        MasterUserPassword=password,
        VpcSecurityGroupIds=[sg_rds],
        DBSubnetGroupName=R["db_subnet_group"],
        PubliclyAccessible=False,
        MultiAZ=False,
        BackupRetentionPeriod=0,
        DeletionProtection=False,
        Tags=config.ETIQUETAS,
    )
    log(f"RDS {ident}: creándose (MariaDB {version}, {R['rds_clase']}); tarda ~10 min")


# ---------------------------------------------------------------- EC2
def buscar_ec2(ec2):
    reservas = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Name", "Values": [R["ec2_nombre"]]},
            {"Name": "tag:Project", "Values": [config.PROYECTO]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]
    )["Reservations"]
    instancias = [i for r in reservas for i in r["Instances"]]
    return instancias[0] if instancias else None


def asegurar_ec2(ec2, ssm, sg_ec2):
    inst = buscar_ec2(ec2)
    if inst:
        estado = inst["State"]["Name"]
        log(f"EC2 {R['ec2_nombre']}: ya existe ({inst['InstanceId']}, {estado})")
        if estado == "stopped":
            ec2.start_instances(InstanceIds=[inst["InstanceId"]])
            log(f"EC2 {R['ec2_nombre']}: arrancando")
        return inst["InstanceId"]

    ami = ssm.get_parameter(Name=AMI_PARAM)["Parameter"]["Value"]
    inst = ec2.run_instances(
        ImageId=ami,
        InstanceType=R["ec2_tipo"],
        MinCount=1,
        MaxCount=1,
        KeyName=R["ec2_llave"],
        IamInstanceProfile={"Name": R["ec2_perfil"]},
        SecurityGroupIds=[sg_ec2],
        UserData=USER_DATA,
        MetadataOptions={"HttpTokens": "required"},
        BlockDeviceMappings=[
            {
                "DeviceName": "/dev/xvda",
                "Ebs": {"VolumeSize": 20, "VolumeType": "gp3", "DeleteOnTermination": True},
            }
        ],
        TagSpecifications=[
            {"ResourceType": "instance", "Tags": config.etiquetas(R["ec2_nombre"])},
            {"ResourceType": "volume", "Tags": config.etiquetas(R["ec2_nombre"])},
        ],
    )["Instances"][0]
    log(f"EC2 {R['ec2_nombre']}: creada ({inst['InstanceId']}, {R['ec2_tipo']}, AMI {ami})")
    return inst["InstanceId"]


# ---------------------------------------------------------------- main
def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-esperar", action="store_true", help="no esperar a que RDS y EC2 estén disponibles")
    args = parser.parse_args()

    cfg = config.cargar()
    aws = config.sesion(cfg)
    s3, ec2, rds, ssm = (aws.client(s) for s in ("s3", "ec2", "rds", "ssm"))
    region = aws.region_name

    print("Datalake")
    bucket = config.nombre_bucket(aws)
    asegurar_bucket(s3, bucket)

    print("Red")
    vpc = vpc_por_defecto(ec2)
    sg_ec2 = asegurar_sg(ec2, vpc, R["sg_ec2"], "SSH a la EC2 de archivos (proyecto2-sd)")
    sg_rds = asegurar_sg(ec2, vpc, R["sg_rds"], "MariaDB desde la EC2 y Glue (proyecto2-sd)")
    ssh = cfg.get("SSH_CIDR") or ip_publica()
    permitir(ec2, sg_ec2, {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
                           "IpRanges": [{"CidrIp": ssh, "Description": "SSH"}]})
    permitir(ec2, sg_rds, {"IpProtocol": "tcp", "FromPort": 3306, "ToPort": 3306,
                           "UserIdGroupPairs": [{"GroupId": sg_ec2, "Description": "MariaDB desde la EC2"}]})
    permitir(ec2, sg_rds, {"IpProtocol": "tcp", "FromPort": 0, "ToPort": 65535,
                           "UserIdGroupPairs": [{"GroupId": sg_rds, "Description": "Glue JDBC (autorreferencia)"}]})
    log(f"reglas: SSH desde {ssh}; 3306 desde {R['sg_ec2']}; TCP dentro de {R['sg_rds']}")
    asegurar_endpoint_s3(ec2, vpc, region)

    print("Fuente: RDS MariaDB")
    asegurar_subnet_group(rds, ec2, vpc)
    asegurar_rds(rds, cfg, sg_rds)

    print("Fuente: archivos en EC2")
    instancia = asegurar_ec2(ec2, ssm, sg_ec2)

    if args.no_esperar:
        print("Listo (sin esperar). Vuelve a correr el script para ver el estado final.")
        return

    print("Esperando a que la EC2 esté corriendo…")
    ec2.get_waiter("instance_running").wait(InstanceIds=[instancia])
    print("Esperando a que la RDS esté disponible (puede tardar ~10 min)…")
    rds.get_waiter("db_instance_available").wait(
        DBInstanceIdentifier=R["rds_id"], WaiterConfig={"Delay": 30, "MaxAttempts": 60}
    )

    inst = ec2.describe_instances(InstanceIds=[instancia])["Reservations"][0]["Instances"][0]
    db = rds.describe_db_instances(DBInstanceIdentifier=R["rds_id"])["DBInstances"][0]
    print("\nResumen")
    log(f"bucket:   s3://{bucket}")
    log(f"EC2:      {instancia}  {inst.get('PublicDnsName') or '(sin DNS público)'}")
    log(f"          ssh -i labsuser.pem ec2-user@{inst.get('PublicIpAddress', '?')}")
    log(f"RDS:      {db['Endpoint']['Address']}:{db['Endpoint']['Port']}  base '{R['rds_db']}', usuario '{R['rds_usuario']}'")


if __name__ == "__main__":
    main()

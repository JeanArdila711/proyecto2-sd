#!/usr/bin/env python3
"""Hive en EMR sobre el Glue Data Catalog (Punto 5): un cluster de un nodo que corre hive.q y se apaga solo.

  - Hive usa el Glue Data Catalog como metastore (clasificación hive-site,
    https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-hive-metastore-glue.html): ve las tablas que
    creó catalogo.py sin DDL propio.
  - Un solo nodo m5.xlarge (el m5 más chico de EMR 7.x), KeepJobFlowAliveWhenNoSteps=False y el step con
    TERMINATE_CLUSTER: el cluster termina al acabar el step, salga bien o mal. Los límites de EMR de
    Academy no se conocen (findings.md): nada de clusters grandes ni encendidos de más.
  - La salida del step queda en s3://<bucket>/emr-logs/ y el script la imprime al terminar.

Uso (desde la raíz del repo):
  python punto5-catalogo/emr_hive.py            # muestra qué lanzaría, sin crear nada
  python punto5-catalogo/emr_hive.py --lanzar   # lanza, espera a que termine (~10-15 min) y muestra la salida
"""
import argparse
import gzip
import json
import sys
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parent))

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

LIBERACION = "emr-7.14.0"  # la que aceptó la API en Academy (findings.md, límites de Academy)
TIPO = "m5.xlarge"
SCRIPT = DIR / "hive.q"
CLAVE_SCRIPT = R["s3_prefijo_codigo"] + "punto5-catalogo/hive.q"
PREFIJO_LOGS = "emr-logs/"


def subred(ec2):
    """Una subred de la VPC por defecto en una zona que ofrezca TIPO (no todas las de us-east-1 lo tienen)."""
    zonas = {o["Location"] for o in ec2.describe_instance_type_offerings(
        LocationType="availability-zone", Filters=[{"Name": "instance-type", "Values": [TIPO]}])[
        "InstanceTypeOfferings"]}
    vpc = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"][0]["VpcId"]
    subredes = ec2.describe_subnets(Filters=[{"Name": "vpc-id", "Values": [vpc]},
                                             {"Name": "default-for-az", "Values": ["true"]}])["Subnets"]
    validas = sorted((s["AvailabilityZone"], s["SubnetId"]) for s in subredes if s["AvailabilityZone"] in zonas)
    if not validas:
        raise SystemExit(f"Ninguna subred de la VPC por defecto está en una zona con {TIPO}")
    return validas[0][1]


def solicitud(bucket, subnet):
    return dict(
        Name="tlc-hive",
        ReleaseLabel=LIBERACION,
        Applications=[{"Name": "Hive"}],
        LogUri=f"s3://{bucket}/{PREFIJO_LOGS}",
        Configurations=[{"Classification": "hive-site", "Properties": {
            "hive.metastore.client.factory.class":
                "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"}}],
        Instances={"InstanceGroups": [{"Name": "primario", "InstanceRole": "MASTER", "InstanceType": TIPO,
                                       "InstanceCount": 1}],
                   "KeepJobFlowAliveWhenNoSteps": False, "TerminationProtected": False, "Ec2SubnetId": subnet},
        Steps=[{"Name": "hive.q", "ActionOnFailure": "TERMINATE_CLUSTER", "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": ["hive-script", "--run-hive-script", "--args", "-f", f"s3://{bucket}/{CLAVE_SCRIPT}"]}}],
        JobFlowRole="EMR_EC2_DefaultRole",
        ServiceRole="EMR_DefaultRole",
        VisibleToAllUsers=True,
        Tags=[{"Key": "Project", "Value": config.PROYECTO}],
    )


def salida_step(s3, bucket, cluster, step):
    """stdout del step; EMR lo sube a S3 unos minutos después de terminar."""
    clave = f"{PREFIJO_LOGS}{cluster}/steps/{step}/stdout.gz"
    for _ in range(20):
        try:
            return gzip.decompress(s3.get_object(Bucket=bucket, Key=clave)["Body"].read()).decode()
        except s3.exceptions.NoSuchKey:
            time.sleep(30)
    return f"(no apareció s3://{bucket}/{clave})"


def esperar(emr, cluster, tope_min):
    """Espera a que el cluster termine. Si pasa tope_min, lo termina (un step colgado nunca deja el cluster
    sin steps, y seguiría cobrando). Devuelve (descripción del cluster, segundos)."""
    inicio = time.time()
    while (c := emr.describe_cluster(ClusterId=cluster)["Cluster"])["Status"]["State"] not in (
            "TERMINATED", "TERMINATED_WITH_ERRORS"):
        transcurrido = time.time() - inicio
        if transcurrido > tope_min * 60:
            print(f"  Pasaron {tope_min} min: termino el cluster {cluster}.", flush=True)
            emr.terminate_job_flows(JobFlowIds=[cluster])
            tope_min = float("inf")  # una sola vez; después solo espera a que quede TERMINATED
        print(f"  {c['Status']['State']}... {transcurrido:.0f} s", flush=True)
        time.sleep(30)
    return c, time.time() - inicio


def vaciar(s3, bucket, prefijo):
    """Borra todo bajo un prefijo, para que una corrida fallida no deje pasar resultados de la anterior."""
    if not prefijo.endswith("/") or prefijo.count("/") < 3:  # nunca "" ni "resultados/": borraría de más
        raise ValueError(f"prefijo demasiado amplio para vaciar: {prefijo!r}")
    for pag in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefijo):
        if claves := [{"Key": o["Key"]} for o in pag.get("Contents", [])]:
            s3.delete_objects(Bucket=bucket, Delete={"Objects": claves, "Quiet": True})


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lanzar", action="store_true")
    args = p.parse_args()
    aws = config.sesion(config.cargar())
    emr, s3 = aws.client("emr"), aws.client("s3")
    bucket = config.nombre_bucket(aws)
    req = solicitud(bucket, subred(aws.client("ec2")))
    activos = emr.list_clusters(ClusterStates=["STARTING", "BOOTSTRAPPING", "RUNNING", "WAITING"])["Clusters"]
    if activos:
        raise SystemExit(f"Ya hay clusters activos: {[c['Id'] for c in activos]}. Uno a la vez.")
    if not args.lanzar:
        print(json.dumps(req, indent=1))
        print(f"\nhive.q:\n{SCRIPT.read_text()}\nNo se lanzó nada. Para lanzar: --lanzar")
        return
    s3.upload_file(str(SCRIPT), bucket, CLAVE_SCRIPT)
    cluster = emr.run_job_flow(**req)["JobFlowId"]
    step = emr.list_steps(ClusterId=cluster)["Steps"][0]["Id"]
    print(f"Cluster {cluster} lanzado; se apaga solo al terminar el step (tope 60 min).", flush=True)
    c, segundos = esperar(emr, cluster, 60)
    estado_step = emr.describe_step(ClusterId=cluster, StepId=step)["Step"]["Status"]
    print(f"Cluster {c['Status']['State']} en {segundos:.0f} s "
          f"({c['Status']['StateChangeReason'].get('Message', '')}). Step: {estado_step['State']}")
    if estado_step["State"] in ("COMPLETED", "FAILED"):  # un step cancelado no deja logs
        print(salida_step(s3, bucket, cluster, step))
    sys.exit(0 if estado_step["State"] == "COMPLETED" else 1)


if __name__ == "__main__":
    main()

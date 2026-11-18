#!/usr/bin/env python3
"""Punto 7 en EMR: preguntas.py (PySpark, API de DataFrames) en un cluster de un nodo que se apaga solo.

Mismo entorno que el SparkSQL del Punto 6 (punto6-analitica-sql/emr.py): emr-7.14.0, un m5.xlarge, Spark
con el Glue Data Catalog como metastore (spark-hive-site), KeepJobFlowAliveWhenNoSteps=False y nunca dos
clusters a la vez. Un solo step: spark-submit de preguntas.py, que deja cada resultado en
s3://<bucket>/resultados/punto7/pyspark/{pN}/.

Uso (desde la raíz del repo):
  python punto7-analitica-pyspark/emr.py            # muestra el cluster, sin crear nada
  python punto7-analitica-pyspark/emr.py --lanzar   # lanza, espera a que termine y muestra la salida
  python punto6-analitica-sql/comparar.py --con-pyspark   # PySpark contra Athena, Hive y SparkSQL
"""
import argparse
import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(DIR.parent), str(DIR.parent / "punto5-catalogo")]

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

import emr_hive  # noqa: E402  (Punto 5: LIBERACION, TIPO, subred, salida_step, PREFIJO_LOGS)

CLAVE_SCRIPT = R["s3_prefijo_codigo"] + "punto7-analitica-pyspark/preguntas.py"
RESULTADOS = R["resultados_prefijo"] + "punto7/pyspark/"
GLUE = "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"


def solicitud(bucket, subnet):
    return dict(
        Name=R["emr_analitica"],
        ReleaseLabel=emr_hive.LIBERACION,
        Applications=[{"Name": "Spark"}],
        LogUri=f"s3://{bucket}/{emr_hive.PREFIJO_LOGS}",
        Configurations=[
            {"Classification": "spark-hive-site", "Properties": {"hive.metastore.client.factory.class": GLUE}}],
        Instances={"InstanceGroups": [{"Name": "primario", "InstanceRole": "MASTER",
                                       "InstanceType": emr_hive.TIPO, "InstanceCount": 1}],
                   "KeepJobFlowAliveWhenNoSteps": False, "TerminationProtected": False, "Ec2SubnetId": subnet},
        Steps=[{"Name": "punto7-pyspark", "ActionOnFailure": "TERMINATE_CLUSTER", "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": ["spark-submit", "--deploy-mode", "client", f"s3://{bucket}/{CLAVE_SCRIPT}",
                     R["glue_base"], f"s3://{bucket}/{RESULTADOS}"]}}],
        JobFlowRole="EMR_EC2_DefaultRole",
        ServiceRole="EMR_DefaultRole",
        VisibleToAllUsers=True,
        Tags=[{"Key": "Project", "Value": config.PROYECTO}],
    )


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lanzar", action="store_true")
    p.add_argument("--tope-min", type=int, default=120,
                   help="minutos antes de terminar el cluster a la fuerza (por defecto 120)")
    args = p.parse_args()
    aws = config.sesion(config.cargar())
    emr, s3 = aws.client("emr"), aws.client("s3")
    bucket = config.nombre_bucket(aws)
    req = solicitud(bucket, emr_hive.subred(aws.client("ec2")))
    activos = emr.list_clusters(ClusterStates=["STARTING", "BOOTSTRAPPING", "RUNNING", "WAITING"])["Clusters"]
    if activos:
        raise SystemExit(f"Ya hay clusters activos: {[c['Id'] for c in activos]}. Uno a la vez.")
    if not args.lanzar:
        print(json.dumps(req, indent=1).replace(bucket, "<bucket>"))
        print("No se lanzó nada. Para lanzar: --lanzar")
        return
    s3.upload_file(str(DIR / "preguntas.py"), bucket, CLAVE_SCRIPT)
    emr_hive.vaciar(s3, bucket, RESULTADOS)
    cluster = emr.run_job_flow(**req)["JobFlowId"]
    step = emr.list_steps(ClusterId=cluster)["Steps"][0]["Id"]
    print(f"Cluster {cluster} lanzado; se apaga solo al terminar el step (tope {args.tope_min} min). "
          f"Si esta terminal se corta: aws emr terminate-clusters --cluster-ids {cluster}", flush=True)
    c, segundos = emr_hive.esperar(emr, cluster, args.tope_min)
    estado = emr.describe_step(ClusterId=cluster, StepId=step)["Step"]["Status"]["State"]
    print(f"Cluster {c['Status']['State']} en {segundos:.0f} s. Step: {estado}")
    if estado in ("COMPLETED", "FAILED"):
        print(emr_hive.salida_step(s3, bucket, cluster, step)[-4000:])
    sys.exit(0 if estado == "COMPLETED" else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Punto 6 en EMR: Hive y SparkSQL sobre el Glue Data Catalog, en un cluster de un nodo que se apaga solo.

Sigue el patrón de punto5-catalogo/emr_hive.py (de ahí salen la liberación, el tipo de máquina y la elección
de subred): un solo m5.xlarge, KeepJobFlowAliveWhenNoSteps=False, nunca dos clusters a la vez.
Dos steps, en orden:
  1. Hive: un .q con P1–P6, cada una como INSERT OVERWRITE DIRECTORY en resultados/punto6/hive/{pN}/.
  2. SparkSQL: spark-submit de sparksql.py, que corre las mismas consultas con spark.sql() y escribe en
     resultados/punto6/sparksql/{pN}/.
Los dos leen tlc_trusted del Glue Data Catalog: Hive por hive-site y Spark por spark-hive-site
(https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-glue.html). Si el step de Hive falla, el de
Spark corre igual (ActionOnFailure=CONTINUE); el cluster termina al acabar el último.

Uso (desde la raíz del repo):
  python punto6-analitica-sql/emr.py            # muestra el cluster y el .q de Hive, sin crear nada
  python punto6-analitica-sql/emr.py --lanzar   # lanza, espera a que termine y muestra la salida de cada step
"""
import argparse
import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(DIR.parent), str(DIR), str(DIR.parent / "punto5-catalogo")]

from comun import config  # noqa: E402
from comun.config import RECURSOS as R  # noqa: E402

import consultas  # noqa: E402
import emr_hive  # noqa: E402  (Punto 5: LIBERACION, TIPO, subred, salida_step, PREFIJO_LOGS)

PREFIJO = R["s3_prefijo_codigo"] + "punto6-analitica-sql/"
GLUE = "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory"


def solicitud(bucket, subnet):
    preguntas = list(consultas.preguntas())
    return dict(
        Name=R["emr_analitica"],
        ReleaseLabel=emr_hive.LIBERACION,
        Applications=[{"Name": "Hive"}, {"Name": "Spark"}],
        LogUri=f"s3://{bucket}/{emr_hive.PREFIJO_LOGS}",
        Configurations=[
            {"Classification": "hive-site", "Properties": {"hive.metastore.client.factory.class": GLUE}},
            {"Classification": "spark-hive-site", "Properties": {"hive.metastore.client.factory.class": GLUE}},
        ],
        Instances={"InstanceGroups": [{"Name": "primario", "InstanceRole": "MASTER",
                                       "InstanceType": emr_hive.TIPO, "InstanceCount": 1}],
                   "KeepJobFlowAliveWhenNoSteps": False, "TerminationProtected": False, "Ec2SubnetId": subnet},
        Steps=[
            {"Name": "punto6-hive", "ActionOnFailure": "CONTINUE", "HadoopJarStep": {
                "Jar": "command-runner.jar",
                "Args": ["hive-script", "--run-hive-script", "--args", "-f", f"s3://{bucket}/{PREFIJO}punto6.q"]}},
            {"Name": "punto6-sparksql", "ActionOnFailure": "CONTINUE", "HadoopJarStep": {
                "Jar": "command-runner.jar",
                "Args": ["spark-submit", "--deploy-mode", "client", f"s3://{bucket}/{PREFIJO}sparksql.py",
                         R["glue_base"], f"s3://{bucket}/{PREFIJO}sparksql/",
                         f"s3://{bucket}/{consultas.RESULTADOS}sparksql/", *preguntas]}},
        ],
        JobFlowRole="EMR_EC2_DefaultRole",
        ServiceRole="EMR_DefaultRole",
        VisibleToAllUsers=True,
        Tags=[{"Key": "Project", "Value": config.PROYECTO}],
    )


def publicar(s3, bucket):
    """Sube el .q de Hive, sparksql.py y las consultas renderizadas para Spark."""
    s3.put_object(Bucket=bucket, Key=PREFIJO + "punto6.q", Body=consultas.script_hive(bucket).encode())
    s3.upload_file(str(DIR / "sparksql.py"), bucket, PREFIJO + "sparksql.py")
    for p in consultas.preguntas():
        s3.put_object(Bucket=bucket, Key=f"{PREFIJO}sparksql/{p}.sql",
                      Body=consultas.render(p, "sparksql").encode())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--lanzar", action="store_true")
    p.add_argument("--tope-min", type=int, default=180,
                   help="minutos antes de terminar el cluster a la fuerza (por defecto 180)")
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
        print("\nHive (punto6.q):\n" + consultas.script_hive("<bucket>"))
        print("No se lanzó nada. Para lanzar: --lanzar")
        return
    publicar(s3, bucket)
    for motor in ("hive", "sparksql"):
        emr_hive.vaciar(s3, bucket, f"{consultas.RESULTADOS}{motor}/")
    cluster = emr.run_job_flow(**req)["JobFlowId"]
    print(f"Cluster {cluster} lanzado; se apaga solo al terminar los steps (tope {args.tope_min} min). "
          f"Si esta terminal se corta: aws emr terminate-clusters --cluster-ids {cluster}", flush=True)
    c, segundos = emr_hive.esperar(emr, cluster, args.tope_min)
    print(f"Cluster {c['Status']['State']} en {segundos:.0f} s "
          f"({c['Status']['StateChangeReason'].get('Message', '')})")
    ok = True
    for step in reversed(emr.list_steps(ClusterId=cluster)["Steps"]):  # list_steps viene del más nuevo
        estado = step["Status"]["State"]
        ok &= estado == "COMPLETED"
        print(f"\n== Step {step['Name']}: {estado}")
        if estado in ("COMPLETED", "FAILED"):
            print(emr_hive.salida_step(s3, bucket, cluster, step["Id"])[-4000:])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

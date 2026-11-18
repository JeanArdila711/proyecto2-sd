"""Punto 6 con SparkSQL: corre en EMR como step de spark-submit (lo lanza emr.py).

Lee las tablas de tlc_trusted desde el Glue Data Catalog (clasificación spark-hive-site del cluster) y
ejecuta con spark.sql() las mismas consultas que Athena y Hive. Cada resultado queda como un CSV con
encabezado en <salida>{pregunta}/ (s3://<bucket>/resultados/punto6/sparksql/).

Las consultas ya vienen renderizadas para Spark por emr.py (consultas.render(p, "sparksql")) en
<consultas>{pregunta}.sql. La base y las dos rutas las pasa emr.py desde comun/config.py.

  spark-submit sparksql.py <base> <s3://.../sparksql/> <s3://.../resultados/punto6/sparksql/> p1 ... p6
"""
import sys
import time

from pyspark.sql import SparkSession

base, consultas, salida, preguntas = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
spark = SparkSession.builder.appName("tlc-punto6-sparksql").enableHiveSupport().getOrCreate()
spark.sql(f"USE {base}")
for p in preguntas:
    inicio = time.time()
    sql = spark.read.text(f"{consultas}{p}.sql", wholetext=True).first()[0]
    df = spark.sql(sql)  # transformación: todavía no se lee nada de S3
    # La escritura es la acción que dispara el job. coalesce(1): un solo CSV; el resultado es pequeño.
    df.coalesce(1).write.mode("overwrite").option("header", True).csv(f"{salida}{p}/")
    n = spark.read.option("header", True).csv(f"{salida}{p}/").count()
    print(f"{p}: {n} filas en {time.time() - inicio:.1f} s", flush=True)
spark.stop()

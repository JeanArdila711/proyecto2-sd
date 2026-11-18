"""Punto 7: P1–P6 con la API de DataFrames de PySpark (sin spark.sql). Corre en EMR como step (lo lanza emr.py).

Lee las tablas de tlc_trusted desde el Glue Data Catalog (spark.table) y responde cada pregunta con las
mismas definiciones del Punto 6 (punto6-analitica-sql/consultas/pN_*.sql): mismas banderas, misma métrica
y mismas columnas de salida, para que comparar.py pueda contrastarlas con Athena, Hive y SparkSQL.
Cada resultado queda como un CSV con encabezado en s3://<bucket>/resultados/punto7/pyspark/{pregunta}/.

  spark-submit preguntas.py <base> <s3://.../resultados/punto7/pyspark/> [p1 ... p6]

La base y el destino los pasa emr.py desde comun/config.py, para no repetirlos aquí.
"""
import sys
import time

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

ZONAS_DESCONOCIDAS = (264, 265)
MILLAS_MAX = 100  # P2 y P5: yellow tiene viajes con miles de millas (ver p2_costo_milla.sql)


def no(*banderas):
    """NOT b1 AND NOT b2 ...: las banderas de calidad son booleanas y nunca NULL en trusted."""
    cond = F.lit(True)
    for b in banderas:
        cond = cond & ~F.col(b)
    return cond


def compania_hvfhv():
    return (F.when(F.col("hvfhs_license_num") == "HV0003", "uber")
            .when(F.col("hvfhs_license_num") == "HV0005", "lyft").otherwise("otra"))


def pct(numerador, denominador):
    return F.round(100 * numerador / denominador, 4)


def p1(spark):
    """Participación de mercado por borough de origen y mes."""
    agregado = (spark.table("viajes")
                .where(no("fuera_de_mes") & ~F.col("pu_zona_id").isin(*ZONAS_DESCONOCIDAS))
                .groupBy("year", "month", "pu_borough", "compania")
                .agg(F.count("*").alias("viajes")))
    w = Window.partitionBy("year", "month", "pu_borough")
    return (agregado.select("year", "month", F.col("pu_borough").alias("borough"), "compania", "viajes",
                            pct(F.col("viajes").cast("double"), F.sum("viajes").over(w)).alias("participacion_pct"))
            .orderBy("year", "month", "borough", "compania"))


def p2(spark):
    """Costo por milla (tarifa_base + recargos) / millas, yellow vs Uber y Lyft, por zona y hora."""
    return (spark.table("viajes")
            .where(F.col("servicio").isin("yellow", "hvfhv") & F.col("compania").isin("yellow", "uber", "lyft")
                   & no("fuera_de_mes", "duracion_invalida", "distancia_invalida", "monto_negativo",
                        "zona_desconocida")
                   & (F.col("millas") <= MILLAS_MAX))
            .groupBy("compania", "pu_zona_id", "pu_borough", "pu_zona", "pickup_hour")
            .agg(F.count("*").alias("viajes"),
                 F.round(F.sum("millas"), 2).alias("millas"),
                 F.round(F.sum(F.col("tarifa_base") + F.col("recargos")) / F.sum("millas"), 4).alias("costo_por_milla"))
            .select("compania", F.col("pu_zona_id").alias("zona_id"), F.col("pu_borough").alias("borough"),
                    F.col("pu_zona").alias("zona"), F.col("pickup_hour").alias("hora"),
                    "viajes", "millas", "costo_por_milla")
            .orderBy("compania", "zona_id", "hora"))


def hvfhv_con_borough(spark):
    zonas = spark.table("taxi_zones").select(F.col("locationid").alias("pulocationid"), "borough")
    # broadcast: 265 filas; cada executor recibe la tabla entera y el join no necesita shuffle
    return spark.table("hvfhv").join(F.broadcast(zonas), "pulocationid").withColumn("compania", compania_hvfhv())


def p3(spark):
    """% de lo que paga el pasajero que recibe el conductor (driver_pay + tips), por compañía, borough y hora."""
    c = lambda col: F.coalesce(F.col(col), F.lit(0.0))  # noqa: E731
    pagado = (c("base_passenger_fare") + c("tolls") + c("bcf") + c("sales_tax") + c("congestion_surcharge")
              + c("airport_fee") + c("cbd_congestion_fee") + c("tips"))
    return (hvfhv_con_borough(spark)
            .where(no("fuera_de_mes", "monto_negativo", "zona_desconocida"))
            .groupBy("compania", "borough", F.col("pickup_hour").alias("hora"))
            .agg(F.count("*").alias("viajes"),
                 pct(F.sum(c("driver_pay") + c("tips")), F.sum(pagado)).alias("pct_conductor"))
            .orderBy("compania", "borough", "hora"))


def p4(spark):
    """Espera desde la solicitud hasta el pickup (promedio y % de más de 10 min), esperas de hasta 1 hora."""
    return (hvfhv_con_borough(spark)
            .where(no("fuera_de_mes", "espera_negativa", "zona_desconocida")
                   & F.col("espera_seg").isNotNull() & (F.col("espera_seg") <= 3600))
            .groupBy("compania", "borough", F.col("pickup_hour").alias("hora"))
            .agg(F.count("*").alias("viajes"),
                 F.round(F.avg("espera_seg") / 60, 4).alias("espera_promedio_min"),
                 F.round(100 * F.avg(F.when(F.col("espera_seg") > 600, 1.0).otherwise(0.0)), 4)
                 .alias("pct_mas_10_min"))
            .orderBy("compania", "borough", "hora"))


def p5(spark):
    """Propina en yellow (solo tarjeta) por hora, tramo de distancia, zona de origen y aeropuerto."""
    z = spark.table("taxi_zones")
    zo = z.select(F.col("locationid").alias("pulocationid"), F.col("borough").alias("o_borough"),
                  F.col("zone").alias("o_zone"), F.col("service_zone").alias("o_service"))
    zd = z.select(F.col("locationid").alias("dolocationid"), F.col("service_zone").alias("d_service"))
    base = (spark.table("yellow")
            .where((F.col("payment_type") == 1) & (F.col("fare_amount") > 0)
                   & no("fuera_de_mes", "monto_negativo", "duracion_invalida", "distancia_invalida",
                        "zona_desconocida")
                   & (F.col("trip_distance") <= MILLAS_MAX)))
    # Igual que el SQL: hora y distancia sin join; zona_origen une el origen; aeropuerto, origen y destino
    con_origen = base.join(F.broadcast(zo), "pulocationid")
    con_ambas = con_origen.join(F.broadcast(zd), "dolocationid")
    d = F.col("trip_distance")
    tramo = (F.when(d < 1, "1. menos de 1 mi").when(d < 3, "2. 1 a 3 mi").when(d < 5, "3. 3 a 5 mi")
             .when(d < 10, "4. 5 a 10 mi").when(d < 20, "5. 10 a 20 mi").otherwise("6. 20 a 100 mi"))
    aeropuertos = ["Airports", "EWR"]
    es_aeropuerto = (F.col("ratecodeid").isin(2, 3) | F.col("o_service").isin(*aeropuertos)
                     | F.col("d_service").isin(*aeropuertos))
    dimensiones = {
        "hora": (base, F.lpad(F.col("pickup_hour").cast("string"), 2, "0")),
        "distancia": (base, tramo),
        "zona_origen": (con_origen, F.concat(F.col("o_borough"), F.lit(" / "), F.col("o_zone"))),
        "aeropuerto": (con_ambas, F.when(es_aeropuerto, "aeropuerto").otherwise("no aeropuerto")),
    }
    largo = None
    for nombre, (df, valor) in dimensiones.items():
        parte = df.select(F.lit(nombre).alias("dimension"), valor.alias("valor"), "tip_amount", "fare_amount")
        largo = parte if largo is None else largo.unionByName(parte)
    return (largo.groupBy("dimension", "valor")
            .agg(F.count("*").alias("viajes"),
                 F.round(F.avg("tip_amount"), 4).alias("propina_promedio"),
                 pct(F.sum("tip_amount"), F.sum("fare_amount")).alias("propina_pct"))
            .orderBy("dimension", "valor"))


def p6(spark):
    """Viajes que terminan en la zona de cobro por congestión, por año, mes y compañía."""
    viajes = spark.table("viajes")
    # Zonas donde al menos la mitad de los viajes internos (origen = destino) de 2025 pagan el cargo
    zonas = (viajes.where((F.col("year") == "2025") & (F.col("pu_zona_id") == F.col("do_zona_id"))
                          & no("fuera_de_mes", "zona_desconocida"))
             .groupBy("do_zona_id")
             .agg(F.sum(F.when(F.col("cbd_fee") > 0, 1).otherwise(0)).alias("con_cargo"),
                  F.count("*").alias("internos"))
             .where(2 * F.col("con_cargo") >= F.col("internos"))  # enteros, igual que el SQL
             .select("do_zona_id"))
    agregado = (viajes.where(no("fuera_de_mes", "zona_desconocida"))
                .join(zonas, "do_zona_id", "left_semi")  # semi join: filtra, no agrega columnas
                .groupBy("year", "month", "compania").agg(F.count("*").alias("viajes")))
    w = Window.partitionBy("year", "month")
    return (agregado.select("year", "month", "compania", "viajes",
                            pct(F.col("viajes").cast("double"), F.sum("viajes").over(w)).alias("participacion_pct"))
            .orderBy("year", "month", "compania"))


PREGUNTAS = {"p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5, "p6": p6}


def main():
    base, salida, elegidas = sys.argv[1], sys.argv[2], sys.argv[3:] or list(PREGUNTAS)
    spark = SparkSession.builder.appName("tlc-punto7-pyspark").enableHiveSupport().getOrCreate()
    spark.catalog.setCurrentDatabase(base)
    for p in elegidas:
        inicio = time.time()
        df = PREGUNTAS[p](spark)  # solo arma el plan (transformaciones lazy)
        destino = f"{salida}{p}/"
        df.coalesce(1).write.mode("overwrite").option("header", True).csv(destino)  # acción: aquí corre
        n = spark.read.option("header", True).csv(destino).count()
        print(f"{p}: {n} filas en {time.time() - inicio:.1f} s", flush=True)
    spark.stop()


if __name__ == "__main__":
    main()

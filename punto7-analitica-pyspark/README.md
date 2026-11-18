# Punto 7 — Analítica descriptiva con PySpark

Las seis preguntas de negocio respondidas con la **API de DataFrames de PySpark** (sin `spark.sql`), sobre las mismas tablas de `tlc_trusted` que el [Punto 6](../punto6-analitica-sql/). Cada pregunta usa exactamente las mismas banderas, métricas y columnas que su consulta SQL, así que los resultados se pueden contrastar con Athena, Hive y SparkSQL: en la muestra, los cuatro dan los mismos números.

```
preguntas.py (p1..p6 con DataFrames)
   └─ spark-submit en EMR, un m5.xlarge que se apaga solo (emr.py)
        spark.table("viajes" | "hvfhv" | "yellow" | "taxi_zones")  <- Glue Data Catalog (spark-hive-site)
        └─> s3://<bucket>/resultados/punto7/pyspark/pN/  (CSV con encabezado)
                     │
   punto6-analitica-sql/comparar.py --con-pyspark  ->  OK si coincide con los tres motores SQL
```

## Cómo se traduce cada pregunta

| Pregunta | Operaciones de DataFrame | Equivalente SQL |
|---|---|---|
| P1 Participación por borough y mes | `where` → `groupBy().agg(count)` → `F.sum().over(Window.partitionBy(...))` | `GROUP BY` + `sum() OVER (PARTITION BY ...)` |
| P2 Costo por milla | `where(isin(...) & ~bandera)` → `groupBy().agg(sum(tarifa_base + recargos) / sum(millas))` | `WHERE ... GROUP BY` |
| P3 % al conductor | `join(F.broadcast(zonas))` + `F.when` para la compañía + `F.coalesce` en cada componente | `JOIN taxi_zones` + `CASE` + `coalesce` |
| P4 Espera | `avg(espera_seg)` y `avg(when(espera > 600, 1.0))` | `avg(...)`, `avg(CASE ...)` |
| P5 Propinas | Cuatro `select` (hora, distancia, zona, aeropuerto) unidos con `unionByName` → `groupBy` | `UNION ALL` de cuatro bloques |
| P6 Cobro por congestión | `join(zonas, "do_zona_id", "left_semi")` | `WHERE do_zona_id IN (SELECT ...)` |

Detalles que se ven en el código:
- **`F.broadcast(zonas)`:** `taxi_zones` tiene 265 filas, así que Spark le manda una copia a cada executor y el join no necesita shuffle.
- **`left_semi`:** filtra los viajes cuyo destino está en la zona de cobro sin agregar columnas, como el `IN (subconsulta)` del SQL.
- **Lazy hasta la escritura:** cada `pN(spark)` solo arma el plan; la acción que lo ejecuta es `write.csv(...)`, y Catalyst optimiza el plan igual que en SparkSQL.

## Por qué así

- **Mismo entorno que el SparkSQL del Punto 6:** un EMR de un solo `m5.xlarge` que se apaga solo, con el Glue Data Catalog como metastore. Se toman la liberación, el tipo y la subred de [`punto5-catalogo/emr_hive.py`](../punto5-catalogo/emr_hive.py). Un cluster aparte del Punto 6 para que cada punto se pueda correr solo.
- **Las definiciones de las preguntas se copian a mano del SQL**, no se generan. Lo que garantiza que no se separen es `comparar.py --con-pyspark`: si una cambia y la otra no, deja de dar OK.

## Archivos

| Archivo | Qué hace |
|---|---|
| [`preguntas.py`](preguntas.py) | P1–P6 con DataFrames; corre en EMR y escribe `resultados/punto7/pyspark/pN/` |
| [`emr.py`](emr.py) | Cluster EMR de un nodo con un step de `spark-submit`; sin `--lanzar` solo muestra lo que lanzaría |

## Reproducir

Desde la raíz del repo, con el catálogo del Punto 5 listo y el Punto 6 corrido (para comparar):

```bash
python punto7-analitica-pyspark/emr.py               # muestra el cluster, sin crear nada
python punto7-analitica-pyspark/emr.py --lanzar      # PySpark; se apaga solo
python punto6-analitica-sql/comparar.py --con-pyspark
```

## Evidencias

Pendientes en la cuenta de la demo (Jean): EMR con el cluster terminado y el step `COMPLETED`, y la terminal de `comparar.py --con-pyspark`, con el ID de la cuenta y el sufijo del bucket ocultos.

## Resultados — **muestra** (2026-11-17)

> **Muestra**, no resultados del proyecto: 3 meses (2024-01 a 2024-03, 70,0 M viajes) en la cuenta de Andres. Los resultados finales salen de la cuenta de la demo con los 24 meses.

`emr.py --lanzar` (`emr-7.14.0`, un `m5.xlarge`): el cluster terminó solo en 464 s con el step `COMPLETED`.

```
p1: 68 filas en 26.6 s
p2: 17984 filas en 21.2 s
p3: 242 filas en 18.6 s
p4: 242 filas en 11.2 s
p5: 282 filas en 15.0 s
p6: 0 filas en 2.1 s
```

`comparar.py --con-pyspark`:

```
pregunta     athena      hive  sparksql   pyspark  resultado
p1               68        68        68        68  OK
p2            17984     17984     17984     17984  OK
p3              242       242       242       242  OK
p4              242       242       242       242  OK
p5              282       282       282       282  OK
p6                0         0         0         0  OK
OK: los motores dan los mismos números
```

P6 sale vacía porque la muestra no tiene 2025 (ver el Punto 6).

## Qué tiene que correr Jean en la cuenta de la demo

Después del Punto 6 y sin otro cluster EMR activo:

```bash
git pull
python punto7-analitica-pyspark/emr.py --lanzar
python punto6-analitica-sql/comparar.py --con-pyspark
```

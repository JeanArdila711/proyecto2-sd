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

Capturas del 2026-11-18 en la cuenta de la demo. En las de la consola se ocultaron el ID de la cuenta, el usuario y el sufijo del bucket.

| Figura | Qué muestra |
|---|---|
| [EMR](evidencias/punto7-1-emr-pyspark.jpg) | El cluster `tlc-analitica` del Punto 7 terminado (15 min), con `punto7-pyspark` `Completed` |
| [`comparar.py --con-pyspark`](evidencias/punto7-2-terminal-comparar.png) | PySpark da los mismos números que los tres motores SQL en P1–P6 |

## Resultados — cuenta de la demo, 24 meses (2026-11-18)

`emr.py --lanzar` (`emr-7.14.0`, un `m5.xlarge`): el cluster terminó solo en 927 s (15 min) con el step `COMPLETED`.

```
p1: 537 filas en 76.4 s
p2: 18596 filas en 126.9 s
p3: 253 filas en 109.5 s
p4: 249 filas en 63.3 s
p5: 291 filas en 64.8 s
p6: 96 filas en 125.1 s
```

`comparar.py --con-pyspark`: los cuatro motores dan los mismos números en las seis preguntas (tabla en el [README del Punto 6](../punto6-analitica-sql/README.md#resultados--cuenta-de-la-demo-24-meses-2026-11-18)).

- **P5:** los joins con `taxi_zones` se hacen solo en las ramas que los necesitan (`zona_origen` con el origen, `aeropuerto` con origen y destino), igual que el SQL. Así, un `pulocationid` que no esté en la tabla de zonas no cambia los conteos de `hora` ni de `distancia`.
- **P2 y P5:** el mismo tope de 100 millas que el SQL (`MILLAS_MAX`).
- **P6:** misma zona de cobro que el SQL (38 zonas), con el umbral comparado con enteros (`2 * con_cargo >= internos`).
- La base y la ruta de salida llegan por argumentos desde `emr.py`, que las toma de `comun/config.py`.

## Resultados — muestra (2026-11-17)

3 meses (2024-01 a 2024-03) en la cuenta de Andres: el cluster terminó en 464 s y los cuatro motores coincidieron en P1–P5. P6 salió vacía porque la muestra no tiene 2025.

# Punto 6 — Analítica descriptiva con SQL (Athena, EMR/Hive y SparkSQL)

Las seis preguntas de negocio ([Punto 1](../punto1-caso-de-estudio/)) respondidas con SQL sobre la base `tlc_trusted` del [Punto 5](../punto5-catalogo/), en los tres motores que pide la rúbrica. Cada pregunta se escribe **una sola vez** en un `.sql` y corre igual en los tres; un script comprueba que los tres den los mismos números.

```
consultas/p1..p6.sql ──consultas.render(p, motor)──┬─> Athena (workgroup tlc-consultas)  ─> resultados/punto6/athena/pN/
                                                   └─> EMR, un m5.xlarge que se apaga solo
                                                         ├─ step Hive (punto6.q)        ─> resultados/punto6/hive/pN/
                                                         └─ step SparkSQL (sparksql.py) ─> resultados/punto6/sparksql/pN/
                                                                         │
                                 comparar.py: mismas filas y mismos números en los tres ─> OK
```

## Las consultas

| Pregunta | Archivo | Tabla | Banderas que filtra |
|---|---|---|---|
| P1 Participación de mercado por borough y mes | [`p1_participacion.sql`](consultas/p1_participacion.sql) | `viajes` | `fuera_de_mes`; origen distinto de 264/265 |
| P2 Costo por milla: yellow vs Uber y Lyft, por zona y hora | [`p2_costo_milla.sql`](consultas/p2_costo_milla.sql) | `viajes` | `fuera_de_mes`, `duracion_invalida`, `distancia_invalida`, `monto_negativo`, `zona_desconocida` |
| P3 % de lo que paga el pasajero que recibe el conductor | [`p3_pago_conductor.sql`](consultas/p3_pago_conductor.sql) | `hvfhv` + `taxi_zones` | `fuera_de_mes`, `monto_negativo`, `zona_desconocida` |
| P4 Espera desde la solicitud hasta el pickup | [`p4_espera.sql`](consultas/p4_espera.sql) | `hvfhv` + `taxi_zones` | `fuera_de_mes`, `espera_negativa`, `zona_desconocida`; esperas ≤ 1 h |
| P5 Qué se asocia a propinas más altas en yellow | [`p5_propinas.sql`](consultas/p5_propinas.sql) | `yellow` + `taxi_zones` | `payment_type = 1`, `fare_amount > 0`, `fuera_de_mes`, `monto_negativo`, `duracion_invalida`, `distancia_invalida`, `zona_desconocida` |
| P6 Efecto del cobro por congestión en los viajes hacia la zona | [`p6_congestion.sql`](consultas/p6_congestion.sql) | `viajes` | `fuera_de_mes`, `zona_desconocida` |

Cada `.sql` explica arriba qué responde, la métrica y por qué filtra cada bandera. Las métricas de P2 y P3 son las de las convenciones "Métrica de P2" y "Métrica de P3" (razón de sumas).

## Por qué así

- **Un `.sql` por pregunta para los tres motores.** Si cada motor tuviera su copia, se separarían. Solo hay una diferencia de dialecto: el tipo texto en un `CAST` (`VARCHAR` en Athena, `STRING` en Hive y Spark), que el `.sql` escribe como `{TEXTO}` y [`consultas.py`](consultas.py) reemplaza. Además se quitan los comentarios, porque el CLI de Hive parte las sentencias por `;` también dentro de un comentario.
- **SQL que los tres aceptan igual.** Divisiones con `CAST(... AS DOUBLE)` (en Athena, `bigint / bigint` es división entera), subconsultas en vez de `WITH` (en Hive, el `WITH` va antes del `INSERT OVERWRITE DIRECTORY`) y porcentajes con una ventana sobre la subconsulta agregada.
- **Promedios, no medianas (P4).** Los percentiles son aproximados y cada motor usa otro algoritmo (`approx_percentile`, `percentile_approx`): no darían el mismo número.
- **Hive y SparkSQL en el mismo cluster EMR**, como dos steps. Un solo cluster de un nodo `m5.xlarge` que se apaga solo, siguiendo [`punto5-catalogo/emr_hive.py`](../punto5-catalogo/emr_hive.py), de donde se toman la liberación, el tipo y la elección de subred. Spark lee el Glue Data Catalog con la clasificación `spark-hive-site`. Se descartó correr SparkSQL en un Glue job: sería otro job de Glue en la cuenta (la regla es uno a la vez) y el cluster ya está levantado para Hive.
- **Resultados en `resultados/punto6/{motor}/{pregunta}/`**, fuera de `raw/` y `trusted/`. El Punto 8 grafica desde ahí (Athena cobra por dato escaneado; las gráficas no consultan trusted en vivo).

## Archivos

| Archivo | Qué hace |
|---|---|
| `consultas/p1..p6.sql` | Las seis consultas, con su explicación |
| [`consultas.py`](consultas.py) | Carga y adapta cada consulta a un motor; arma el `.q` de Hive |
| [`test_consultas.py`](test_consultas.py) | Chequeos sin AWS |
| [`athena.py`](athena.py) | Corre las seis en Athena y copia cada CSV a `resultados/punto6/athena/` |
| [`emr.py`](emr.py) | Cluster EMR de un nodo con dos steps, Hive y SparkSQL; sin `--lanzar` solo muestra lo que lanzaría |
| [`sparksql.py`](sparksql.py) | El step de Spark: `spark.sql()` sobre el catálogo y escritura del CSV |
| [`comparar.py`](comparar.py) | Compara los tres motores celda por celda; exit 1 si alguno difiere |

## Reproducir

Desde la raíz del repo, con el catálogo del Punto 5 listo:

```bash
python punto6-analitica-sql/test_consultas.py   # ok
python punto6-analitica-sql/athena.py           # ~1 min, ~14 GiB escaneados con 24 meses
python punto6-analitica-sql/emr.py              # muestra el cluster, sin crear nada
python punto6-analitica-sql/emr.py --lanzar     # Hive + SparkSQL, ~50 min con 24 meses; se apaga solo
python punto6-analitica-sql/comparar.py         # OK si los tres motores coinciden
```

Los resultados quedan en `s3://<bucket>/resultados/punto6/{athena,hive,sparksql}/{p1..p6}/`.

## Evidencias

Pendientes (Jean): consola de Athena con una consulta, EMR con el cluster `tlc-analitica` terminado y sus dos steps `COMPLETED`, y la terminal de `comparar.py`, con el ID de la cuenta y el sufijo del bucket ocultos.

## Resultados — cuenta de la demo, 24 meses (2026-11-18)

Con el tope de 100 millas en P2 y P5 (`findings.md`, "Calidad yellow"): sin él, 2.829 viajes de yellow con miles de millas sumaban el 41 % de sus millas y el taxi amarillo salía como el más barato por milla (4,30 USD) cuando es el más caro (7,31, frente a 6,44 de Uber y 6,34 de Lyft).

2024-01 a 2025-12 de yellow, green y HVFHV en `tlc_trusted` (Punto 5).

`athena.py`:

```
p1: 537 filas, 872.6 MiB escaneados, 5.5 s
p2: 18596 filas, 4,682.4 MiB escaneados, 9.2 s
p3: 253 filas, 4,667.4 MiB escaneados, 6.5 s
p4: 249 filas, 1,634.3 MiB escaneados, 6.5 s
p5: 291 filas, 1,636.8 MiB escaneados, 8.8 s
p6: 96 filas, 1,425.8 MiB escaneados, 8.9 s
Escaneado en total: 14,558.5 MiB
```

`emr.py --lanzar` (`emr-7.14.0`, un `m5.xlarge`): el cluster terminó solo en 47 min, con los dos steps `COMPLETED`: Hive en 32 min y SparkSQL en 10.

`comparar.py --con-pyspark` (después del [Punto 7](../punto7-analitica-pyspark/)):

```
pregunta     athena      hive  sparksql   pyspark  resultado
p1              537       537       537       537  OK
p2            18596     18596     18596     18596  OK
p3              253       253       253       253  OK
p4              249       249       249       249  OK
p5              291       291       291       291  OK
p6               96        96        96        96  OK
OK: los motores dan los mismos números
```

- **Zona de cobro de P6:** 38 zonas, todas de Manhattan (convención "Zonas de cobro por congestión"). La primera versión tomaba toda zona de destino con algún viaje de 2025 con cargo y daba 261, porque el cargo también lo pagan viajes que solo salen del área (hacia JFK, Newark o Brooklyn). Con los viajes internos a cada zona el corte es limpio: las 38 tienen 0,69 o más y la siguiente, 0,44. El umbral se compara con enteros (`2 * sum(...) >= count(*)`) porque `avg(1.0)` es DECIMAL en Athena y DOUBLE en Hive y Spark.
- **Tolerancia de `comparar.py`:** en P2, `millas` (redondeada a 2 decimales) puede diferir en 0,01 entre motores con el mismo costo por milla: cada motor suma los double en otro orden y el total cae en el borde del redondeo. Por eso la tolerancia es una unidad en el segundo decimal. Una pregunta vacía en algunos motores y no en otros es error; vacía en todos solo avisa (P6 en una muestra sin 2025).
- **Corridas limpias:** `athena.py` y los dos `emr.py` borran sus prefijos de `resultados/` antes de correr, así que un motor que falla deja su prefijo vacío y `comparar.py` lo marca. Los `emr.py` terminan el cluster si pasa el tope (`--tope-min`, 180 en este punto) e imprimen el comando para terminarlo a mano si se corta la terminal.

## Resultados — muestra (2026-11-17)

3 meses (2024-01 a 2024-03, 70,0 M viajes) en la cuenta de Andres, para probar el código antes de la cuenta de la demo: Athena, Hive y SparkSQL coincidieron en P1–P5 (68, 17.984, 242, 242 y 282 filas) en un cluster de 805 s. P6 salió vacía porque la muestra no tiene 2025.

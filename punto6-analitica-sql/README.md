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
python punto6-analitica-sql/athena.py           # ~1 min
python punto6-analitica-sql/emr.py              # muestra el cluster, sin crear nada
python punto6-analitica-sql/emr.py --lanzar     # Hive + SparkSQL; se apaga solo
python punto6-analitica-sql/comparar.py         # OK si los tres motores coinciden
```

Los resultados quedan en `s3://<bucket>/resultados/punto6/{athena,hive,sparksql}/{p1..p6}/`.

## Evidencias

Pendientes en la cuenta de la demo (Jean): consola de Athena con una consulta, EMR con el cluster `tlc-analitica` terminado y sus dos steps `COMPLETED`, y la terminal de `comparar.py`, con el ID de la cuenta y el sufijo del bucket ocultos.

## Resultados — **muestra** (2026-11-17)

> **Muestra**, no resultados del proyecto: 3 meses (2024-01 a 2024-03) en la cuenta de Andres. Solo prueban que el código corre y que los tres motores coinciden. Los resultados finales salen de la cuenta de la demo con los 24 meses.

Muestra: 70.026.229 viajes en `viajes` (`punto5-catalogo/verificar.py` en OK).

`athena.py`:

```
p1: 68 filas, 106.4 MiB escaneados, 5.2 s
p2: 17984 filas, 565.8 MiB escaneados, 9.4 s
p3: 242 filas, 573.4 MiB escaneados, 9.9 s
p4: 242 filas, 203.2 MiB escaneados, 4.9 s
p5: 282 filas, 150.9 MiB escaneados, 6.0 s
p6: 0 filas, 0.0 MiB escaneados, 1.6 s
Escaneado en total: 1,599.8 MiB
```

`emr.py --lanzar` (`emr-7.14.0`, un `m5.xlarge`): el cluster terminó solo en 805 s, con los dos steps `COMPLETED`. SparkSQL tardó entre 2,5 y 26 s por pregunta.

`comparar.py`:

```
pregunta     athena      hive  sparksql  resultado
p1               68        68        68  OK
p2            17984     17984     17984  OK
p3              242       242       242  OK
p4              242       242       242  OK
p5              282       282       282  OK
p6                0         0         0  OK
OK: los motores dan los mismos números
```

- **P6 sale vacía en la muestra, como se esperaba:** la zona de cobro se deriva de los viajes de 2025 con `cbd_fee > 0`, y la muestra solo tiene 2024. La consulta corre en los tres motores; su resultado real sale con los 24 meses.
- **Tolerancia de `comparar.py`:** en P2, `millas` (redondeada a 2 decimales) difirió en 0,01 en 368 de 17.984 filas entre motores, con el mismo costo por milla: cada motor suma los double en otro orden y el total cae en el borde del redondeo. Por eso la tolerancia es una unidad en el segundo decimal.

## Qué tiene que correr Jean en la cuenta de la demo

Con el catálogo de los 24 meses ya listo y sin otro cluster EMR activo:

```bash
git pull
python punto6-analitica-sql/test_consultas.py
python punto6-analitica-sql/athena.py
python punto6-analitica-sql/emr.py --lanzar      # un m5.xlarge, se apaga solo
python punto6-analitica-sql/comparar.py
```

Con los 24 meses, Athena escanea unas 8 veces más que en la muestra (unos 13 GiB, ~USD 0,06). El step de Hive en un solo nodo es lo más lento: en la muestra los dos steps tardaron unos 13 min con el arranque; con 8 veces más datos puede pasar de una hora. Si tarda demasiado, se puede subir el nodo a `m5.2xlarge` (aceptado por la API en Academy según `findings.md`, sin probar).

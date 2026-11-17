# Plan: Punto 4, preparación raw → trusted con AWS Glue y Apache Spark
Fecha: 2026-11-15 · Commit base: dff07ac · Input: `proposal.md` § Combinación (1 + 2) y § Dirección elegida

## Contexto actual

- Raw en la cuenta de Jean: 24 meses (2024-01 a 2025-12) de yellow, green y HVFHV, un Parquet por mes en `raw/{dataset}/year=YYYY/month=MM/`, más `raw/taxi_zones/taxi_zones.parquet` (research § Zona raw tal como está).
- No hay nada del Punto 4: ni código (`punto4-preparacion/README.md:1-3`), ni `trusted/`, ni recursos de Glue o Step Functions en la cuenta (research § AWS Glue).
- `comun/config.py:19-44` (`RECURSOS`) no tiene claves de Glue, Step Functions ni trusted.
- `punto3-ingesta/lambda_ingesta.py:156-172` es el handler de la ingesta. Termina con `raise RuntimeError` si hubo errores y no dispara nada después.
- `punto3-ingesta/desplegar.py:57-73` arma las variables de entorno de la Lambda; `:76-108` es el patrón de upsert que se copia.
- Esquema de green: `punto2-fuentes/ec2/esquema.sql:14-44`. No tiene `airport_fee`.

## Estado final esperado

- `trusted/{yellow,green,hvfhv}/year=YYYY/month=MM/` con los 72 meses y `trusted/taxi_zones/`, todos en Parquet con nombres y tipos canónicos, columnas derivadas y banderas de calidad.
- `trusted/viajes/servicio=X/year=YYYY/month=MM/` con los 72 meses, generada en la misma pasada.
- `trusted/_control/` con un JSON por (dataset, mes): filas de raw, filas escritas, conteo por bandera y esquema escrito.
- La state machine `tlc-preparacion` procesa solo lo que falta. Una segunda ejecución seguida no lanza ningún job.
- La Lambda `tlc-ingesta` inicia `tlc-preparacion` al terminar cada corrida, o, si `LabRole` no lo permite, queda documentado el plan B (`preparar_local.py`).
- Se comprueba con los conteos de `_control/` (raw = detalle = viajes, por mes), con `preparar_local.py --estado` (0 pendientes) y con las evidencias del README.

## Requisitos

- Funcionales:
  - Procesamiento raw → trusted con AWS Glue (Spark), automático y encadenado con la ingesta (Docx ¶20; convención "Ingesta automática").
  - Las preguntas se responden desde trusted: P1, P2 y P6 desde `viajes`; P3, P4 y P5 desde la tabla de su servicio (convención "Layout de la zona trusted").
  - Ninguna fila se borra. La calidad se marca con banderas.
  - Reprocesar un mes reemplaza exactamente su partición en cada salida.
- No funcionales:
  - Glue 5.0 y `G.1X` fijos; `LabRole` en todo (convención "Roles de AWS Academy").
  - Infraestructura con scripts boto3 idempotentes, etiqueta `Project`, nombres en `RECURSOS` (convención "Infraestructura por scripts").
  - Sin IDs de cuenta ni credenciales en el repo.
  - Costo acotado: $0,44 por DPU-hora en us-east-1 (Glue 2.0 a 5.1), con facturación por segundo y mínimo de 1 minuto (https://aws.amazon.com/glue/pricing/, consultado el 2026-11-15).

## Decisiones de diseño

### Un control propio en `trusted/_control/` decide qué falta
El job escribe `trusted/_control/{dataset}/{YYYY-MM}.json` (y `trusted/_control/taxi_zones.json`) como último paso, después de escribir las salidas y verificar los conteos. Un par (dataset, mes) está pendiente si su control no existe o si su `LastModified` es anterior al del archivo de raw. Así, un job que se cae a mitad de escritura deja el mes pendiente, y la siguiente ejecución lo rehace. Descartado:
- comparar contra el `LastModified` de los part-files de trusted, porque unos archivos parciales de un job caído quedan más nuevos que raw y el mes parecería hecho;
- los job bookmarks de Glue, porque están documentados para DynamicFrames y un reset no limpia los destinos (research § AWS Glue).

El prefijo `_control/` queda fuera de las rutas de las tablas, así que el Punto 5 no lo cataloga.

### Overwrite en la ruta explícita de la partición
Cada salida se escribe con `mode("overwrite")` en la ruta completa de su partición (`s3://<bucket>/trusted/green/year=2024/month=01/`), igual que `m4-raw-to-structured/raw_to_structured.py:163-170`. `year`, `month` y `servicio` no van como columnas en el Parquet: salen de la ruta, que es como las cataloga el Punto 5. Descartado: `partitionOverwriteMode=dynamic`. Funcionaría (`spark.conf.set` es válido en Spark 3.5.4), pero la documentación de EMR pide modo `static` para usar el committer optimizado de S3 con overwrite de Parquet particionado (https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-spark-committer-reqs.html), y con una sola partición por corrida no aporta nada. Las rutas siempre con `s3://`.

### "Qué falta" lo calcula una Lambda dentro de la state machine
Primer estado: la Lambda `tlc-preparacion-pendientes`, que lista `raw/` y `trusted/_control/` y devuelve la lista de pares pendientes con su número de workers. Segundo: un `Map` sobre `glue:startJobRun.sync`. La lógica vive en `pendientes.py`, Python puro con test. Lo usan la Lambda y `preparar_local.py --estado`, así que la ejecución automática, la manual y un reintento ven lo mismo. Descartado: ASL puro con `aws-sdk:s3:listObjectsV2` y JSONata, porque comparar fechas ahí es frágil, la paginación es manual y no se puede probar localmente.

### La Lambda de ingesta dispara siempre, salvo que ya haya una ejecución en curso
Al final del handler, `lambda_ingesta.py` llama `list_executions(statusFilter="RUNNING", maxResults=1)`. Si no hay ninguna, llama `start_execution`. No mira si subió algo, porque eso obligaría a interpretar la salida de la EC2, que puede seguir corriendo cuando la Lambda termina; lo que llegue tarde lo toma la corrida siguiente. Una ejecución sin pendientes cuesta una invocación de Lambda y unas pocas transiciones. Si la llamada falla, el error va a `resumen["preparacion"]`, no a `resumen["errores"]`, para no tumbar la ingesta (mismo criterio que `lambda_ingesta.py:162`). Descartado: una regla de EventBridge directa a la state machine, porque la trust policy de `LabRole` no incluye `events.amazonaws.com` (proposal § Dirección elegida).

### `viajes` se materializa
Una vista normal de Athena solo es visible en Athena: "the Apache Hive, Apache Spark, and Athena views are created independently in each analytics service [...] and are visible and accessible only within that service" (https://docs.aws.amazon.com/lake-formation/latest/dg/working-with-views.html). Las vistas multi-dialecto del Data Catalog no soportan Hive en EMR y requieren Lake Formation y un rol definer, que Academy no deja crear. Por eso `viajes` va como Parquet, escrita en la misma pasada que el detalle.

### Nombres canónicos
- Todo en minúscula: `Airport_fee` → `airport_fee`, `PULocationID` → `pulocationid`.
- Los tiempos de yellow y green se renombran a los de HVFHV: `tpep_/lpep_pickup_datetime` → `pickup_datetime`, y lo mismo con `dropoff`. Así las derivadas y las banderas usan las mismas columnas en los tres servicios.
- `taxi_zones`: `locationid` int, y `borough`, `zone`, `service_zone` string. Los textos `"Unknown"` y `"N/A"` de las zonas 264 y 265 se dejan tal cual; el CSV oficial dice `264,"Unknown","N/A","N/A"` y `265,"N/A","Outside of NYC","N/A"` (https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv, descargado el 2026-11-15).

### Archivos por partición
`repartition(n)` con `n = ceil(bytes del archivo de raw / 256 MiB)`: 1 archivo en green y yellow, 2 en HVFHV. Descartado: `coalesce(n)`, porque baja a `n` tareas todo el stage, incluidas la lectura y la transformación. En HVFHV eso dejaría 2 tareas con 10 workers.

### Workers y concurrencia
- Workers por dataset, en `RECURSOS["glue_workers"]`. Valores iniciales: `taxi_zones` 2, `green` 2, `yellow` 4 y `hvfhv` 10. El mínimo de Glue Spark es 2 DPU; 10 es lo único probado en Academy (`findings.md:35-39`). Yellow y HVFHV se ajustan en la tarea 4.1 con lo medido.
- `MaxConcurrency` del `Map` y `MaxConcurrentRuns` del job: 3, en `RECURSOS["preparacion_concurrencia"]`.
- Job con `MaxRetries=0` y timeout de 60 min. El reintento es la ejecución siguiente, como en la ingesta.

## Diseño técnico

### Contrato (`punto4-preparacion/contrato.py`, Python puro)

```python
# Por dataset: columna de raw -> (nombre en trusted, tipo Spark, obligatoria)
DETALLE = {
  "yellow": {"VendorID": ("vendorid", "int", True), "tpep_pickup_datetime": ("pickup_datetime", "timestamp", True), ...,
             "cbd_congestion_fee": ("cbd_congestion_fee", "double", False)},
  "green":  {...},
  "hvfhv":  {...},
  "taxi_zones": {...},
}
DESCARTADAS = {"green": {"trip_id", "mes_archivo", "cargado_en"}}
TARIFA = {  # componentes de viajes por servicio (fase 5)
  "yellow": {"tarifa_base": ["fare_amount"], "recargos": ["extra", "mta_tax", "improvement_surcharge",
             "congestion_surcharge", "airport_fee", "cbd_congestion_fee"], "peajes": ["tolls_amount"],
             "propina": ["tip_amount"]},
  "green":  {... "recargos": ["extra", "mta_tax", "improvement_surcharge", "congestion_surcharge",
             "ehail_fee", "cbd_congestion_fee"] ...},
  "hvfhv":  {"tarifa_base": ["base_passenger_fare"], "recargos": ["bcf", "sales_tax", "congestion_surcharge",
             "airport_fee", "cbd_congestion_fee"], "peajes": ["tolls"], "propina": ["tips"]},
}
def familia(tipo_spark) -> str          # "entero" | "decimal" | "texto" | "tiempo"
def validar(dataset, esquema_raw)        # lista de errores: falta una obligatoria, sobra una
                                         # desconocida, o el tipo de raw no es de la familia del destino
```

- Las columnas de yellow y HVFHV son las de research § Zona raw tal como está. Las de green salen de `esquema.sql:14-44`.
- Las columnas no obligatorias que faltan, en la práctica `cbd_congestion_fee` en 2024, se agregan como `NULL` del tipo destino.
- Se trabaja con nombres en minúscula después del cast. Los mapeos de `TARIFA` usan esos nombres.

### Derivadas y banderas (detalle, los tres servicios)

| Columna | Definición |
|---|---|
| `pickup_date`, `pickup_hour` | de `pickup_datetime` |
| `duracion_min` | `(dropoff − pickup)` en minutos, double |
| `espera_seg` (solo hvfhv) | `pickup_datetime − request_datetime` en segundos, long |
| `fuera_de_mes` | `date_format(pickup_datetime, 'yyyy-MM') != mes` |
| `duracion_invalida` | `dropoff <= pickup` o alguno NULL |
| `distancia_invalida` | `trip_distance` (`trip_miles` en hvfhv) `<= 0` o NULL |
| `monto_negativo` | algún componente de `TARIFA` del servicio `< 0` |
| `zona_desconocida` | `pulocationid` o `dolocationid` en (264, 265) |
| `espera_negativa` (solo hvfhv) | `espera_seg < 0` |
| `pago_mayor_a_tarifa` (solo hvfhv) | `driver_pay > base_passenger_fare` |

Las banderas son boolean y nunca NULL (`coalesce(..., false)`). `taxi_zones` no lleva derivadas ni banderas.

### `viajes` (fase 5)

`servicio`, `compania`, `pickup_datetime`, `dropoff_datetime`, `pickup_date`, `pickup_hour`, `duracion_min`, `pu_zona_id`, `pu_borough`, `pu_zona`, `pu_service_zone`, los mismos cuatro para `do_`, `millas`, `tarifa_base`, `recargos`, `peajes`, `propina`, `cbd_fee`, `total_pagado` y las banderas comunes (`fuera_de_mes`, `duracion_invalida`, `distancia_invalida`, `monto_negativo`, `zona_desconocida`).
- `compania`: `yellow` y `green` por servicio; en HVFHV, `uber` (HV0003), `lyft` (HV0005) y `otra` para cualquier otro valor (`findings.md:11-15`).
- Cada componente es la suma de sus columnas con `coalesce(x, 0)`. `total_pagado` es `total_amount` en yellow y green, y la suma de los cuatro componentes en HVFHV.
- Las zonas salen de un join broadcast con `raw/taxi_zones/taxi_zones.parquet`, que tiene 265 filas, para no depender del orden contra `trusted/taxi_zones`. Un ID fuera de 1–265 queda con zona NULL y se cuenta en el control como `sin_zona`.

### Glue job (`preparar.py`)
- Argumentos: `--dataset`, `--mes` (`YYYY-MM`, o `na` para `taxi_zones`) y `--bucket`.
- Pasos:
  1. Listar la partición de raw; debe haber exactamente un objeto.
  2. Leerlo con `spark.read.parquet` y `validar()`. Si hay errores, `raise` antes de escribir.
  3. Cast y renombre; derivadas y banderas.
  4. `repartition(n)` y escribir el detalle.
  5. Escribir `viajes`, desde la fase 5.
  6. Releer lo escrito y comparar el conteo con raw. Si no coincide, `raise` sin escribir el control.
  7. Escribir el control.
- `contrato.py` llega al job por `--extra-py-files`.

### Control (`trusted/_control/{dataset}/{mes}.json`)
`{"dataset", "mes", "raw": {"clave", "bytes", "last_modified"}, "filas_raw", "filas_detalle", "filas_viajes", "banderas": {nombre: n}, "sin_zona", "esquema_detalle": [[col, tipo]], "job_run_id", "escrito_en"}`. `filas_viajes` y `sin_zona` aparecen desde la fase 5.

### State machine `tlc-preparacion`

```
Pendientes (arn:aws:states:::lambda:invoke, OutputPath $.Payload)
  -> Procesar (Map, ItemsPath $.pendientes, MaxConcurrency = preparacion_concurrencia)
       -> Job (arn:aws:states:::glue:startJobRun.sync,
               JobName, WorkerType G.1X, NumberOfWorkers.$ $.workers,
               Arguments {"--dataset.$": "$.dataset", "--mes.$": "$.mes"})
```
- La Lambda devuelve `{"pendientes": [{"dataset", "mes", "workers"}]}`.
- Si un job falla, el `Map` falla y la ejecución termina en FAILED. Lo que quedó pendiente lo toma la siguiente.

## Archivos

- Se crean:
  - `punto4-preparacion/contrato.py`: esquemas, mapeos de tarifa, `familia()` y `validar()`.
  - `punto4-preparacion/preparar.py`: el Glue job.
  - `punto4-preparacion/pendientes.py`: `pendientes(raw, controles, workers)` sobre dos dict `{clave: LastModified}`. Es puro, y su regex de partición es la de `punto3-ingesta/ingestar.py:25`.
  - `punto4-preparacion/lambda_pendientes.py`: lista S3 y llama `pendientes()`.
  - `punto4-preparacion/desplegar.py`: publica el código y crea o actualiza el job, la Lambda de pendientes y la state machine. Tiene `--borrar`.
  - `punto4-preparacion/preparar_local.py`: `--estado`, `--ejecutar`, `--forzar --dataset D --mes M` y `--forzar --todo`. El forzado borra controles y ejecuta la state machine.
  - `punto4-preparacion/test_contrato.py` y `punto4-preparacion/test_pendientes.py`: asserts y `print("ok")`, como `punto3-ingesta/test_raw.py`.
  - `punto4-preparacion/evidencias/`: capturas.
- Se tocan:
  - `comun/config.py`: claves nuevas en `RECURSOS` (`glue_job_preparacion`, `lambda_pendientes`, `sm_preparacion`, `trusted_prefijo`, `control_prefijo`, `glue_workers`, `preparacion_concurrencia`).
  - `punto3-ingesta/lambda_ingesta.py`: `disparar_preparacion(resumen)` al final del handler, antes del `raise`.
  - `punto3-ingesta/desplegar.py`: variable de entorno `SM_PREPARACION_ARN` en `variables()`.
  - `punto4-preparacion/README.md`: el README completo del punto.
  - `docs/design/findings.md`: permisos de `LabRole` y lo medido en Glue.
- NO se tocan:
  - `punto3-ingesta/raw.py`, `ec2_ingesta.py` e `ingestar.py`: el layout de raw no cambia.
  - `punto2-fuentes/infra/crear_infra.py` y `destruir_infra.py`: el SG autorreferenciado y el endpoint de S3 quedan fuera de alcance.
  - El Docx y Obsidian: van cuando haya evidencias, en otra sesión.

## Fuera de alcance

- Las definiciones de P2 y P3 (David). Trusted deja la tarifa en componentes.
- Catálogo, crawler, Athena y Hive: Punto 5. Las tablas se validan aquí con los conteos de `_control/`.
- Una prueba local con PySpark: la prueba de la transformación es la corrida en Glue de la fase 1.
- Glue Flex ($0,29 por DPU-hora): es una opción si el costo de la fase 4 lo pide, pero no se usa de entrada porque Flex puede arrancar tarde.
- Alertas por fallas de la state machine.
- Borrar `trusted/` desde `desplegar.py --borrar`: los datos quedan, como en el Punto 3.

## Fase 0: Credenciales y permisos de `LabRole`
Saber qué permite `LabRole` antes de escribir código. Si `StartExecution` está denegado, la fase 3 pasa al plan B.

- [x] 0.1 Pedirle a Jean credenciales nuevas de Academy en `~/.aws/credentials` bajo `[academy]`, con `AWS_PROFILE=academy` en `config.env`. Confirmar con `aws sts get-caller-identity --profile academy --region us-east-1 --query Arn --output text | sed 's/[0-9]\{12\}/<cuenta>/'`, sin imprimir el ID. [independiente]
- [x] 0.2 Prueba con recursos `tlc-prueba-*`, todos con CLI (`--profile academy --region us-east-1`) y archivos en el scratchpad de la sesión, no en el repo [depende de 0.1]:
  1. Subir un script `print("ok")` a `s3://<bucket>/codigo/prueba/prueba.py`. `aws glue create-job` con `--glue-version 5.0 --worker-type G.1X --number-of-workers 2 --role LabRole --command Name=glueetl,...`, después `start-job-run` y `get-job-run` hasta `SUCCEEDED`.
  2. `aws stepfunctions create-state-machine` con `LabRole` y un solo estado `glue:startJobRun.sync` sobre ese job; `start-execution` y `describe-execution` hasta `SUCCEEDED`.
  3. `aws lambda create-function` (python3.12, `LabRole`) con un handler que hace `list_executions(statusFilter="RUNNING")` y `start_execution` sobre esa state machine; `aws lambda invoke` y revisar la respuesta.
  4. Borrar los tres recursos y `codigo/prueba/`.
- [x] 0.3 Registrar el resultado de cada acción, permitida o denegada con el código de error, en `docs/design/findings.md`. [depende de 0.2]

Verificación automática:
- [ ] `aws glue get-jobs --profile academy --region us-east-1 --query 'Jobs[?starts_with(Name, \`tlc-prueba\`)]'`: vacío, sin restos de la prueba.
- [ ] `aws stepfunctions list-state-machines --profile academy --region us-east-1 --query 'stateMachines[?starts_with(name, \`tlc-prueba\`)]'`: vacío.

Verificación manual:
- [ ] Jean lee la entrada de `findings.md` y confirma el camino de la fase 3 (Lambda o plan B).

## Fase 1: Contrato y Glue job de la capa de detalle
`trusted/{yellow,green,hvfhv}` y `trusted/taxi_zones` se generan corriendo el job a mano.

- [x] 1.1 Claves nuevas en `RECURSOS` — `comun/config.py` [independiente]
- [x] 1.2 Contrato: `DETALLE` de los cuatro datasets, `DESCARTADAS`, `TARIFA`, `familia()` y `validar()` — `punto4-preparacion/contrato.py` [independiente]
- [x] 1.3 Test del contrato — `punto4-preparacion/test_contrato.py` [depende de 1.2]. Asserts:
  - el esquema real de raw de cada dataset, escrito como constante en el test a partir de research § Zona raw y `esquema.sql:14-44`, pasa `validar()` sin errores, con y sin `cbd_congestion_fee`;
  - los nombres destino son únicos y están en minúscula;
  - cada columna de `TARIFA` existe en el destino de su dataset;
  - `validar()` reporta una columna obligatoria que falta, una desconocida y un tipo de otra familia.
- [x] 1.4 Glue job con los pasos 1–4, 6 y 7 de § Glue job — `punto4-preparacion/preparar.py` [depende de 1.2]
- [x] 1.5 Despliegue del job: publica `preparar.py` y `contrato.py` en `codigo/punto4-preparacion/` y hace upsert de `tlc-preparacion` (Glue 5.0, `G.1X`, 2 workers por defecto, `MaxRetries=0`, timeout 60, `MaxConcurrentRuns` de `RECURSOS`, `--extra-py-files`, `--bucket`, etiqueta `Project`) — `punto4-preparacion/desplegar.py` [depende de 1.1, 1.4]

Verificación automática:
- [x] `.venv/bin/python punto4-preparacion/test_contrato.py` → `ok`
- [x] `.venv/bin/python punto3-ingesta/test_raw.py` → `ok` (sin regresión)
- [x] `.venv/bin/python punto4-preparacion/desplegar.py` dos veces seguidas: la segunda actualiza y no crea nada nuevo.

Verificación manual:
- [x] `aws glue start-job-run --job-name tlc-preparacion --arguments '{"--dataset":"green","--mes":"2024-01"}'` → `SUCCEEDED`. En el control, `filas_raw == filas_detalle` (46–61 k), el esquema tiene las columnas canónicas sin `trip_id`, `mes_archivo` ni `cargado_en`, y aparecen los conteos de banderas.
- [x] Lo mismo con `taxi_zones` (`--mes na`): 265 filas.
- [x] Lo mismo con yellow 2024-01 y yellow 2025-01: `cbd_congestion_fee` NULL en el primero y con valores en el segundo, y `fuera_de_mes` mayor que 0 en alguno de los dos.
- [x] Repetir green 2024-01: en `aws s3 ls --recursive` de la partición quedan solo los archivos nuevos, sin duplicados.

## Fase 2: Qué falta y state machine
`tlc-preparacion` procesa sola todo lo pendiente.

- [x] 2.1 `pendientes(raw, controles, workers)` según § Un control propio. Ignora en raw lo que no sea `.parquet` — `punto4-preparacion/pendientes.py` [independiente]
- [x] 2.2 Test de pendientes — `punto4-preparacion/test_pendientes.py` [depende de 2.1]. Asserts:
  - sin control → pendiente;
  - control más viejo que raw → pendiente;
  - control más nuevo → no pendiente;
  - `taxi_zones` → `mes "na"`;
  - orden determinista (dataset, mes);
  - workers según el dict.
- [x] 2.3 Handler que lista `raw/` y `trusted/_control/` con paginador y devuelve `{"pendientes": [...]}` — `punto4-preparacion/lambda_pendientes.py` [depende de 2.1]
- [x] 2.4 En `desplegar.py`: upsert de la Lambda `tlc-preparacion-pendientes` (zip con `lambda_pendientes.py` y `pendientes.py`, env `BUCKET` y `WORKERS` en JSON) y de la state machine `tlc-preparacion` (§ State machine; `list_state_machines` por nombre → `update_state_machine` o `create_state_machine` con tags). `--borrar` borra la state machine, la Lambda y el job — `punto4-preparacion/desplegar.py` [depende de 2.3]
- [x] 2.5 CLI local: `--estado` (pendientes con la misma función más un resumen de los controles), `--ejecutar`, `--forzar --dataset --mes` y `--forzar --todo`. Termina con `sys.exit(0/1)` según el resultado de la ejecución, que espera con `describe_execution` — `punto4-preparacion/preparar_local.py` [depende de 2.1]

Verificación automática:
- [x] `.venv/bin/python punto4-preparacion/test_pendientes.py` → `ok`
- [x] `.venv/bin/python punto4-preparacion/desplegar.py` dos veces seguidas sin errores.

Verificación manual:
- [x] `preparar_local.py --estado` lista como pendientes todo menos lo corrido en la fase 1.
- [x] Con `glue_workers` en sus valores iniciales y `--forzar --dataset green --mes 2024-02`, la ejecución termina en `SUCCEEDED` y solo cambia el control de green 2024-02.

## Fase 3: Encadenar con la ingesta
EventBridge → ingesta → preparación, sin intervención. Si la fase 0 dio `StartExecution` denegado, esta fase se reduce a la tarea 3.3, documentando el plan B.

- [x] 3.1 `disparar_preparacion(resumen)` según § La Lambda de ingesta dispara siempre, llamada al final del handler antes del `raise` — `punto3-ingesta/lambda_ingesta.py` [independiente]
- [x] 3.2 `SM_PREPARACION_ARN` en `variables()`, armado con región, cuenta y `RECURSOS["sm_preparacion"]` — `punto3-ingesta/desplegar.py` [independiente]
- [ ] 3.3 Sección "Encadenamiento" del README del punto: cómo se dispara y el plan B — `punto4-preparacion/README.md` [depende de 3.1]

Verificación automática:
- [x] `.venv/bin/python -c "import ast,sys; ast.parse(open('punto3-ingesta/lambda_ingesta.py').read())"` y `.venv/bin/python punto3-ingesta/desplegar.py` sin errores, con la RDS encendida o al menos con endpoint (ver Riesgos).

Verificación manual:
- [x] Borrar `trusted/_control/green/2024-03.json`, correr `.venv/bin/python punto3-ingesta/ingestar.py` (la EC2 puede estar apagada: esa parte se omite) y ver que el resumen trae `preparacion` con un ARN de ejecución. La ejecución reprocesa solo green 2024-03.
- [x] Invocar dos veces seguidas: la segunda dice "ya hay una ejecución en curso" o encuentra 0 pendientes.
- [x] `punto3-ingesta/desplegar.py --pausar` al terminar.

## Fase 4: Dimensionar y hacer la carga completa
Los 72 meses en la capa de detalle, con tiempos y costo medidos.

- [x] 4.1 HVFHV 2025-12 (22,1 M filas, el más grande) con `--forzar` y 10 workers. Anotar la duración y los DPU-hora de `get-job-run` (`ExecutionTime`, `DPUSeconds` si viene). Con eso fijar `glue_workers` de hvfhv y yellow en `RECURSOS`, buscando que un mes de HVFHV tarde menos de 15 min, y estimar el costo total — `comun/config.py`, `docs/design/findings.md` [independiente]
- [x] 4.2 `preparar_local.py --ejecutar` hasta 0 pendientes. Evidencias: consola de la state machine con el `Map` y consola de S3 en `trusted/` — sin archivos [depende de 4.1]
- [x] 4.3 Agregar en `--estado` una tabla de los controles: por dataset, meses, filas de raw, filas de detalle y suma de banderas — `punto4-preparacion/preparar_local.py` [depende de 4.2]

Verificación automática:
- [x] `.venv/bin/python punto4-preparacion/preparar_local.py --estado`: 0 pendientes, 73 controles y `filas_raw == filas_detalle` en todos. Termina con código 0, o 1 si hay alguna diferencia.

Verificación manual:
- [x] `--ejecutar` otra vez: el `Map` recibe 0 elementos y no se lanza ningún job (consola de Glue sin corridas nuevas).
- [x] `--forzar --dataset yellow --mes 2024-06`: cambian solo los archivos de esa partición y su control (comparar `LastModified` con `aws s3 ls --recursive` antes y después).
- [x] Revisar el costo acumulado de la carga contra la estimación de 4.1.

## Fase 5: `trusted/viajes`
Segunda salida del mismo job (proposal § Dirección elegida, ajuste 1).

- [x] 5.1 Columnas de `viajes` y mapeo de `compania` en el contrato; asserts nuevos en el test: cada columna de `viajes` tiene origen en los tres servicios o es NULL a propósito, y no hay columnas de `TARIFA` repetidas entre componentes de un servicio — `punto4-preparacion/contrato.py`, `punto4-preparacion/test_contrato.py` [independiente]
- [x] 5.2 Paso 5 de § Glue job: proyección, componentes, join broadcast con zonas, escritura en `trusted/viajes/servicio=X/year=/month=/` y `filas_viajes` y `sin_zona` en el control — `punto4-preparacion/preparar.py` [depende de 5.1]
- [x] 5.3 Redesplegar, correr green 2024-01 con `--forzar`, revisar y después `--forzar --todo` para los 72 meses [depende de 5.2]

Verificación automática:
- [x] `.venv/bin/python punto4-preparacion/test_contrato.py` → `ok`
- [x] `preparar_local.py --estado`: 0 pendientes y `filas_raw == filas_detalle == filas_viajes` en los 72 meses.

Verificación manual:
- [x] En el control de green 2024-01, `sin_zona` es 0 y las banderas coinciden con las de la fase 1.
- [x] En el control de un mes de HVFHV, `filas_viajes` es igual a `filas_detalle`.

## Fase 6: README y evidencias
El Punto 4 queda reproducible desde el repo (Docx ¶26).

- [ ] 6.1 README con la estructura de `punto3-ingesta/README.md`: diagrama, "Por qué así" con lo descartado (las decisiones de este plan), layout de trusted, contrato y banderas, idempotencia, tabla de archivos, Reproducir, Evidencias y Resultados (conteos de `--estado`, tiempos y costo) — `punto4-preparacion/README.md` [independiente]
- [ ] 6.2 Capturas en `punto4-preparacion/evidencias/`: consola de Glue con las corridas, state machine con el `Map`, S3 `trusted/`, un control abierto y terminal de `--estado` [independiente]

Verificación automática:
- [ ] `grep -rnE '[0-9]{12}' punto4-preparacion/` sin resultados (ningún ID de cuenta).

Verificación manual:
- [ ] Jean sigue "Reproducir" del README en una sesión nueva de Academy y llega al mismo `--estado`.
- [ ] Al terminar: `punto3-ingesta/desplegar.py --pausar` y `punto2-fuentes/infra/apagar_infra.py`, si se encendió algo.

## Riesgos y rollback

- **`LabRole` deniega algo de Glue o de Step Functions.** La fase 0 lo descubre antes de escribir código.
  - Si falta `glue:CreateJob`, se para y se le pregunta a Jean, porque no hay plan B con Glue.
  - Si falla la state machine, se le pregunta a Jean antes de cambiar la orquestación.
  - Si solo falla `StartExecution` desde la Lambda, se aplica el plan B.
- **Límite de DPU concurrentes en Academy, sin verificar.** 3 jobs de HVFHV con 10 workers son 30 DPU. Si Glue rechaza corridas por capacidad, se baja `preparacion_concurrencia` a 1 y se redespliega.
- **Credenciales que expiran en medio de la carga.** La state machine sigue corriendo en AWS; lo que no termine queda pendiente y se retoma con `--ejecutar`.
- **`punto3-ingesta/desplegar.py` necesita el endpoint de la RDS** (`desplegar.py:58-60`). Si con la RDS detenida `describe_db_instances` no trae `Endpoint`, hay que encenderla con `crear_infra.py` para la fase 3 y apagarla después.
- **Rollback:**
  - `punto4-preparacion/desplegar.py --borrar` quita el job, la Lambda y la state machine. Los datos de `trusted/` quedan.
  - Para empezar de cero, `aws s3 rm s3://<bucket>/trusted/ --recursive`. Raw no se toca en ningún paso.

## Notas de implementación

**2026-11-15, sesión 1:**
- Sin credenciales de Academy al arrancar (no existe el perfil `academy`). Se escribió el código de las fases 1, 2 y 3 antes de la fase 0, porque solo depende del resultado de la fase 0 si se niega `glue:CreateJob`, y `findings.md:35-39` ya registra un job `G.1X` aceptado. Si la fase 0 deniega `StartExecution`, `disparar_preparacion` deja el error en `resumen["preparacion"]` y se aplica el plan B.
- Desvío del plan, a favor: el job **borra el control del mes antes de escribir** (paso 3 de `preparar.py`). Sin eso, si un reproceso forzado se cae a mitad de escritura, el control viejo seguiría más nuevo que raw y el mes parecería hecho con la partición rota.
- La capa de layout de trusted (`prefijo_trusted`, `clave_control`) vive en `pendientes.py`, que también viaja al job por `--extra-py-files`, para que el job, la Lambda y `preparar_local.py` usen las mismas rutas.
- `desplegar.py` ya tiene el job, la Lambda de pendientes y la state machine (1.5 y 2.4 juntos); falta correrlo en AWS. `preparar_local.py --estado` ya incluye la tabla de controles de 4.3.
- Pendiente para seguir: credenciales → fase 0 → `desplegar.py` → verificaciones manuales de la fase 1.
- Revisión del `revisor` (sin AWS) aplicada:
  - El `Job` del `Map` descarta su salida (`ResultPath: null`) en vez de un `ResultSelector`, porque `ExecutionTime` es opcional en `JobRun` y un path ausente tumba la iteración.
  - Desvío del plan: un mes que falla ya no frena a los demás. `Catch` → `Anotar falla`, y después del `Map` un `Pass` filtra `$[?(@.error)]` y un `Choice` termina en `Fail` si hubo alguno. La ejecución igual queda FAILED, pero procesa todo lo demás. *Sin verificar en AWS* que el filtro JSONPath funcione en `Parameters`; se prueba en la fase 2.
  - `preparar.py` vuelve a leer el archivo de raw antes de escribir el control y falla si cambió durante el job (carrera con la EC2).
  - `preparar_local.py --forzar` aborta si hay una ejecución en curso, y valida `--mes`.
  - `disparar_preparacion` captura también `BotoCoreError` y usa timeouts cortos.
- La fase 0 está en el scratchpad de la sesión (`fase0/probar.sh`). El hook de guardia bloquea los borrados de AWS que hace el script, así que lo corre Jean con `!`.

**2026-11-15, sesión 1 (AWS):**
- Fase 0 hecha (`findings.md`, "LabRole alcanza para Glue 5.0 y Step Functions"). Todo está permitido, también `StartExecution` desde la Lambda, así que la fase 3 va por la Lambda y no hace falta el plan B. Se agregó un `Retry` para `Glue.ConcurrentRunsExceededException` al `Job` del `Map`. Los recursos `tlc-prueba-permisos` siguen en la cuenta: hay que borrarlos con `scratchpad/fase0/limpiar.sh`, que corre Jean con `!` porque el guard bloquea los borrados de AWS. Mientras no se borren, las dos verificaciones automáticas de la fase 0 quedan sin marcar.
- `desplegar.py` creó y después actualizó el job, la Lambda y la state machine.
- Fase 1, resultados en Glue:
  - green 2024-01: SUCCEEDED en 75 s y 150 DPU-s. Raw = detalle = 56.551 filas, sin columnas de auditoría. Banderas: `fuera_de_mes` 2, `duracion_invalida` 76, `distancia_invalida` 2.870, `monto_negativo` 186 y `zona_desconocida` 643.
  - `taxi_zones`: SUCCEEDED en 55 s, 265 filas.
  - yellow 2024-01 y 2025-01, con 4 workers: SUCCEEDED en 99 s y 102 s (396 y 411 DPU-s). Sus controles no se pudieron leer porque Academy revocó las credenciales (`voc-cancel-cred`).
- Arreglo: `duracion_min` salía `decimal(27,6)`, porque `60.0` es un literal decimal en Spark SQL. Ahora divide por `60D`. Green 2024-01 hay que repetirlo para que quede en double; los yellow ya corrieron con el arreglo.
- Para retomar:
  1. Credenciales nuevas en `scratchpad/aws/credentials` (perfil `academy`), con `AWS_SHARED_CREDENTIALS_FILE`.
  2. Leer los controles de yellow 2024-01 y 2025-01.
  3. Repetir green 2024-01 (prueba de idempotencia).
  4. Seguir con las verificaciones manuales de la fase 1 y después la fase 2.

**2026-11-15, sesión 1 (cuenta nueva, segundo curso de Jean):**
- La cuenta del primer curso quedó desactivada al correr tres jobs a la vez (`findings.md`). Jean pasó a la cuenta de su segundo curso: se replicaron los Puntos 2 y 3 (`crear_infra`, `sembrar`, `simular` 2024-01..2025-12, `desplegar` e `ingestar`) y raw quedó con los 72 archivos y `taxi_zones` en una corrida. La regla de ingesta quedó **pausada**. Se cambió la convención "Cuenta de la demo".
- Desvío del plan por seguridad: `glue_workers` en 2 para todos los datasets y `preparacion_concurrencia` en 1, hasta conocer los límites de Glue de Vocareum. La tarea 4.1 ya no mide con 10 workers. Si Jean consigue los límites, se mide con más; si no, se queda en 2.
- Los jobs se corren **de a uno**, con `scratchpad/correr_job.sh`. El script verifica que la cuenta esté activa, que no haya corridas activas y reintenta solo el `ConcurrentRunsExceeded`.
- Fase 1 en la cuenta nueva, todo con 2 workers:

  | Mes | Estado | Tiempo | DPU-s | Filas raw = detalle |
  |---|---|---|---|---|
  | green 2024-01 | SUCCEEDED | 94 s | 188 | 56.551 |
  | `taxi_zones` | SUCCEEDED | 74 s | — | 265 |
  | yellow 2024-01 | SUCCEEDED | 91 s | 182 | 2.964.624 |
  | yellow 2025-01 | SUCCEEDED | 98 s | 196 | 3.475.226 |

  - Las banderas de green son idénticas a las de la cuenta anterior.
  - `duracion_min` sale `double`.
  - Al repetir green 2024-01, la partición quedó con 1 archivo nuevo del mismo tamaño, sin duplicados.
  - Sin verificar: que `cbd_congestion_fee` sea NULL en 2024 y tenga valores en 2025. El control no cuenta nulos; se ve con Athena en el Punto 5.

**2026-11-16, carga completa (cuenta nueva):**
- HVFHV 2025-12, solo y con 2 workers: 227 s y 455 DPU-s, 22.108.438 filas en 2 archivos. Se dejó `glue_workers` en 2 para todo (4.1), por los límites desconocidos de Vocareum. El investigador no encontró valores publicados; solo el mecanismo ("Glue Max Workers", "Glue Max Concurrent jobs", "Glue Worker Types"). Hay que pedírselos al profesor.
- Carga completa con una ejecución de `tlc-preparacion` (68 meses, de a uno, 2 workers): **SUCCEEDED en 13.795 s (3 h 50 min)**, sin ningún job fallido. A mitad de la carga se reinició la sesión del lab ("Start Lab") y la carga siguió sin cortes, con las mismas credenciales.
- `--estado`: 0 pendientes, 73 controles, raw = detalle en todos:

  | Dataset | Filas | Banderas principales |
  |---|---|---|
  | green | 1.251.593 | `distancia_invalida` 4,71 %, `zona_desconocida` 1,42 % |
  | hvfhv | 483.060.132 | `pago_mayor_a_tarifa` 12,88 %, `zona_desconocida` 4,37 %, `espera_negativa` 1,06 %, `fuera_de_mes` 0 |
  | yellow | 89.892.322 | `monto_negativo` 3,99 %, `distancia_invalida` 2,42 % |
  | `taxi_zones` | 265 | — |

- Idempotencia: una segunda `--ejecutar` terminó SUCCEEDED en 30 s y no lanzó ningún job (74 corridas de Glue antes y después).
- La EC2 y la RDS de la cuenta nueva quedaron detenidas (`apagar_infra.py`). La regla de ingesta sigue pausada.
- Faltan:
  - fase 2, verificación manual de `--forzar` de un mes;
  - fase 3, verificación manual del encadenamiento: borrar un control y correr `ingestar.py`;
  - fase 4, `--forzar` de yellow 2024-06;
  - fases 5 (`viajes`, que reprocesa los 72 meses, ~4 h con 2 workers) y 6;
  - la limpieza de `tlc-prueba-permisos` no aplica: esos recursos estaban en la cuenta desactivada.


**2026-11-16, sesión 2 (cuenta nueva):**
- Verificaciones manuales marcadas por el agente con evidencia, sin una corrida aparte de Jean:
  - Fases 2 y 4: `--forzar --dataset yellow --mes 2024-06` terminó SUCCEEDED en 211 s. El diff de `aws s3 ls --recursive trusted/` antes y después solo muestra el part-file nuevo y el control de ese mes. El ítem de green 2024-02 de la fase 2 queda cubierto por esta misma prueba.
  - Fase 3: se borró el control de green 2024-03 y se corrió `ingestar.py`. La Lambda inició la ejecución, que rehízo solo green 2024-03 en 128 s. Una segunda invocación, con esa ejecución en curso, devolvió `preparacion: "ya hay una ejecución en curso"`. La parte de la EC2 falló porque la RDS estaba detenida, que era lo esperado. La regla sigue pausada.
  - Costo de la fase 4: 76 corridas, todas SUCCEEDED, ~6,0 DPU-hora, unos USD 2,64 en la cuenta nueva.
- Fase 5, desvíos del plan:
  - `servicio` no se escribe como columna del Parquet de `viajes`: sale de la ruta, igual que `year` y `month`, porque con la columna en los dos lados el catálogo choca con la partición.
  - `viajes` se arma releyendo el detalle ya escrito, no desde raw. Así no hay una segunda lectura de raw ni cache.
  - El paso 5 va después de comparar el conteo del detalle (en el plan iba antes). Es equivalente: el control solo se escribe si las dos comparaciones pasan.
  - `cbd_fee` se deja sin `coalesce`, NULL en 2024. En `recargos` y `total_pagado` sí entra con `coalesce`.
  - `sin_zona` = filas con `pu_borough` o `do_borough` NULL. `raw/taxi_zones` no tiene nulos (verificado con DuckDB: 265 filas, IDs 1–265), así que NULL equivale a que el join no encontró la zona.
  - `--estado` ahora marca como diferencia un control de un servicio sin `filas_viajes` (hallazgo del `revisor`). Se descartó otra sugerencia del revisor, `coalesce(n)` en vez de `repartition(n)`, por la misma razón que dejó el plan en § Archivos por partición.
- green 2024-01 con `viajes`: SUCCEEDED en 181 s. raw = detalle = viajes = 56.551, `sin_zona` 0, banderas idénticas a las de la fase 1 y 26 columnas en `viajes`.
- `--forzar --todo` lanzado el 2026-11-16 ~12:45, de a un job, ~4 h. Al terminar: `--estado` y marcar 5.3 y la verificación de los 72 meses.
- La escritura de Glue deja marcadores `_$folder$` de 0 bytes (`trusted/green/year=2024_$folder$`); quedan para el Punto 5 (`findings.md`).
- "Start Lab" encendió la EC2 detenida y se volvió a apagar (`findings.md`).
- Recarga completa terminada: ejecución SUCCEEDED en 16.848 s (~4 h 41 min), de 12:44 a 17:25. `--estado`: 0 pendientes, 73 controles, sin diferencias (exit 0). Totales: green 1.251.593, hvfhv 483.060.132, yellow 89.892.322 y taxi_zones 265, con raw = detalle = viajes en los 72 meses de servicio. Control de hvfhv 2025-06: 19.868.009 filas en raw, detalle y viajes, y `sin_zona` 0.
- Tiempo de Glue de la recarga: ~219 min de ejecución, ~7,3 DPU-hora, unos USD 3,2 (G.1X con 2 workers, a USD 0,44 por DPU-hora).
- "Start Lab" volvió a encender la EC2 a las 14:46, y se apagó otra vez. Es la segunda vez que pasa.
- Verificación de `cbd_congestion_fee` hecha con Athena en el Punto 5 (2026-11-16): `cbd_fee` de `viajes` es NULL en todo 2024 de los tres servicios y tiene valores en todo 2025 de yellow y HVFHV (green: 587.551 de 591.375). `fuera_de_mes` de yellow suma 634 en los 24 meses.

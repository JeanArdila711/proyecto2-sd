# Research: Punto 4, preparación raw → trusted con AWS Glue y Apache Spark
Fecha: 2026-11-15 · Commit: 8b0d4c1 · Rama: main

## Resumen

La zona raw de la cuenta de Jean tiene los 24 meses (2024-01 a 2025-12) de yellow, green y HVFHV, un Parquet por mes en `raw/{dataset}/year=YYYY/month=MM/`, más `raw/taxi_zones/taxi_zones.parquet`. Los esquemas no coinciden entre datasets: varían tipos, nombres y columnas, como `Airport_fee` frente a `airport_fee` o `int32` frente a `int64`. Yellow y HVFHV ganan `cbd_congestion_fee` en 2025. Green la trae desde 2024 porque sale de MariaDB. Yellow y green tienen viajes con fecha de pickup fuera del mes del archivo, algunos de 2002 a 2009. La cuenta no tiene ningún recurso de Glue ni de Step Functions, y no existe `trusted/`. `LabRole` confía en `glue.amazonaws.com` y en `states.amazonaws.com`. El repo no tiene código, configuración ni nombres para Glue o trusted. El Docx y la rúbrica piden solo "preparación de datos raw → trusted con AWS Glue y Apache Spark", con evidencias. No piden modelo dimensional.

## Stack y arquitectura relevante

- **Datalake:** S3, un solo bucket `proyecto2-tlc-<hash>`. El nombre sale de `sha256(account_id)[:8]` (`comun/config.py:84-87`). Prefijos actuales: `raw/` y `codigo/`.
- **Ingesta (Punto 3):** EventBridge → Lambda `tlc-ingesta` (HVFHV) y SSM → `ec2_ingesta.py` (yellow, green, zonas) → `raw/`. La regla está deshabilitada y la EC2 y la RDS detenidas (`docs/design/CONTEXT.md:38`).
- **Infraestructura:** scripts boto3 idempotentes por punto, con nombres en `comun/config.py` `RECURSOS` (`comun/config.py:19-44`), etiqueta `Project=proyecto2-sd` y `LabRole` (convenciones "Infraestructura por scripts" y "Roles de AWS Academy").
- **Python local:** `.venv` con `boto3>=1.35` (`requirements.txt`). pyarrow no está instalado localmente; solo existe en la EC2 (`punto2-fuentes/ec2/requirements.txt`).

## Hallazgos por área

### Zona raw tal como está (footers leídos el 2026-11-15, script `esquemas_raw.py` en el scratchpad de la sesión)

**yellow**: archivo de la TLC tal cual, 24 archivos, 1,42 GiB.
- Columnas base (2024):
  - `VendorID` int32
  - `tpep_pickup_datetime` y `tpep_dropoff_datetime`, timestamp[us]
  - `passenger_count`, `RatecodeID` y `payment_type`, int64
  - `trip_distance` double
  - `store_and_fwd_flag` large_string
  - `PULocationID` y `DOLocationID`, int32
  - `fare_amount`, `extra`, `mta_tax`, `tip_amount`, `tolls_amount`, `improvement_surcharge`, `total_amount` y `congestion_surcharge`, double
  - `Airport_fee` double, con A mayúscula
- Desde 2025-01 aparece `cbd_congestion_fee` double. No hay otros cambios de nombre ni de tipo en los 24 meses.
- Filas por mes: entre 2,96 M (2024-01) y 4,59 M (2025-05), con 3 a 5 row groups.

**green**: generado desde MariaDB por `ec2_ingesta.py`. Sus tipos vienen del esquema SQL (`punto3-ingesta/README.md:30-40`), con 24 archivos y 0,04 GiB.
- Columnas:
  - `trip_id` int64
  - `VendorID`, `RatecodeID`, `PULocationID`, `DOLocationID`, `passenger_count`, `payment_type` y `trip_type`, int64
  - `lpep_pickup_datetime` y `lpep_dropoff_datetime`, timestamp[us]
  - `store_and_fwd_flag` string
  - `trip_distance` double y los montos en double, incluidos `ehail_fee`, `congestion_surcharge` y `cbd_congestion_fee` (presente también en 2024, en NULL)
  - Columnas extra de la ingesta: `mes_archivo` string y `cargado_en` timestamp[us]
- El esquema es idéntico en los 24 meses. Filas por mes: entre 46 k y 61 k, en 1 row group.

**hvfhv**: archivo de la TLC tal cual, 24 archivos, 10,93 GiB.
- Columnas:
  - `hvfhs_license_num`, `dispatching_base_num` y `originating_base_num`, large_string
  - `request_datetime`, `on_scene_datetime`, `pickup_datetime` y `dropoff_datetime`, timestamp[us]
  - `PULocationID` y `DOLocationID`, int32
  - `trip_miles` double y `trip_time` int64
  - `base_passenger_fare`, `tolls`, `bcf`, `sales_tax`, `congestion_surcharge`, `airport_fee` (minúscula), `tips` y `driver_pay`, double
  - Los flags `shared_request_flag`, `shared_match_flag`, `access_a_ride_flag`, `wav_request_flag` y `wav_match_flag`, large_string
- Desde 2025-01 aparece `cbd_congestion_fee` double.
- Filas por mes: entre 19,1 M y 22,1 M (2025-12), con 19 a 22 row groups. Cada archivo pesa entre 440 y 511 MiB.

**taxi_zones**: desde MariaDB, 265 filas. Columnas: `LocationID` int64, `Borough`, `Zone` y `service_zone`, string.

**Fechas de pickup fuera del mes del archivo** (min y max de las estadísticas del footer):
- Yellow:
  - Mínimos de 2002-12-31 (2024-11), 2007-12-05 (2025-03) y 2008/2009 en varios meses.
  - Máximos que se pasan semanas del mes: 2024-12 llega a 2025-03-23 y 2024-10 a 2024-11-14.
- Green: mínimos de 2008/2009 en 2024-03, 2024-05, 2024-09, 2024-12 y 2025-12. Lo normal es que el rango empiece algunos días antes del mes y termine un día después.
- HVFHV: en los meses con estadísticas, el rango cae exacto dentro del mes.
- Yellow 2024-01 a 2024-07 y HVFHV 2024-01 a 2024-07 no traen estadísticas min/max en el footer, así que el rango de esos meses no se midió.
- No se contó cuántas filas caen fuera del mes, porque las estadísticas solo dan los extremos.

### Requisitos: rúbrica, Docx y preguntas

- **Lo que pide el Punto 4:** "Realizar procesamiento orientado a la Preparación de datos (desde zona raw a trusted, o en medallion: bronze a silver), herramientas a utilizar: AWS Glue y Apache Spark" (Docx ¶20; `docs/design/planificacion/current/rubrica.md:17-28`).
- **Sección del Punto 4 en el Docx:** es una plantilla vacía, `<<descripciones, pantallazos, evidencias, extracto de código, si aplica>>` (Docx ¶279-288).
- **Repo:** cada punto necesita un directorio con instrucciones para reproducirlo (Docx ¶26).
- **Puntos siguientes que consumen trusted:**
  - Punto 5: catalogación con Glue y EMR/Hive (¶21).
  - Punto 6: SQL con Athena, Hive y SparkSQL (¶22).
  - Punto 7: PySpark (¶23).
- **Columnas que piden las preguntas** (`docs/design/planificacion/current/preguntas-de-negocio.md:19-28`):

  | Pregunta | Datasets | Columnas y derivaciones | Estado |
  |---|---|---|---|
  | P1, participación por borough y mes | yellow, green, HVFHV, zonas | conteos, `hvfhs_license_num` (HV0003 = Uber, HV0005 = Lyft), `PULocationID` × `Borough` | definida |
  | P2, costo por milla por zona y hora | yellow, HVFHV | `fare_amount / trip_distance` frente a `base_passenger_fare / trip_miles`, hora, `PULocationID` | abierto qué tarifa se compara (`docs/design/README.md:54`, Proposed) |
  | P3, porcentaje para el conductor | HVFHV | `driver_pay` / denominador, hora, borough | abierto el denominador (`README.md:55`, Proposed) |
  | P4, espera del pasajero | HVFHV | `pickup_datetime − request_datetime`; `on_scene_datetime` descartado porque solo se llena en WAV (`:22`) | definida |
  | P5, propinas | yellow | solo `payment_type = 1`; `tip_amount`, hora, `trip_distance`, `PULocationID`; aeropuerto por `RatecodeID`, `airport_fee` o `service_zone` en Airports/EWR (`:23`) | definida |
  | P6, cobro por congestión | los tres servicios, zonas | `DOLocationID` × zonas con `cbd_congestion_fee > 0` en 2025 (convención "Zonas de cobro por congestión") | definida |

### Calidad de datos registrada (`docs/design/findings.md`)

- `cbd_congestion_fee` no existe en los archivos de 2024 de la TLC (`findings.md:5-9`).
- HVFHV solo tiene Uber (HV0003) y Lyft (HV0005) (`findings.md:11-15`).
- Las propinas solo quedan registradas con tarjeta (`findings.md:17-21`).
- Hay esperas negativas en HVFHV, entre 2.451 y 6.636 por compañía en el row group 0 de 2024-06 y 2025-06. El finding dice que se filtran o se marcan en el Punto 4 (`findings.md:23-27`; Docx ¶76).
- `driver_pay > base_passenger_fare` en el 12–16 % de los viajes de Uber y el 7–8 % de los de Lyft, así que el porcentaje de P3 puede pasar de 100 % (`findings.md:26`; Docx ¶77).
- HVFHV pesa 10,93 GiB y es lo que dimensiona a Glue (`findings.md:29-33`).
- Glue aceptó un job `G.1X` × 10 con Glue 5.0 (`findings.md:35-39`).

### Código existente reutilizable o de referencia en el repo

- `punto3-ingesta/raw.py:9-25`: `PREFIJO="raw/"`, `CLAVE_ZONAS`, `clave(dataset, mes, archivo)` y `meses(desde, hasta)`, un generador inclusivo de "YYYY-MM". No tiene dependencias.
- `ingestar.py:25` usa la regex `raw/([^/]+)/year=(\d{4})/month=(\d{2})/`.
- `punto3-ingesta/desplegar.py`:
  - Publica el código con `s3.upload_file` en `codigo/punto3-ingesta/` (`:31-46`).
  - Hace un upsert del recurso con `get_*`, luego `update_*` o `create_*` con `Tags`, más waiters (`asegurar_lambda`, `:76-108`).
  - Arma el ARN de LabRole desde STS (`:168-171`).
  - Ofrece `--pausar` y `--borrar` en la CLI (`:150-165`). `borrar()` tolera recursos que no existen (`:136-147`).
- `punto3-ingesta/ingestar.py:47-81`: invoca con `retries=0`, `--estado` lista raw por dataset y termina con `sys.exit(0/1)`.
- `comun/config.py`:
  - `cargar()` lee `config.env` (`:49-62`).
  - `sesion(cfg)` (`:77-81`), `nombre_bucket(sesion)` (`:84-87`), `etiquetas()` (`:90-94`).
  - `RECURSOS` no tiene claves de Glue ni de trusted (`:19-44`).
- `punto2-fuentes/infra/crear_infra.py`:
  - Crea en `tlc-rds-sg` una regla TCP 0-65535 autorreferenciada con la descripción "Glue JDBC (autorreferencia)" (`:300-301`).
  - Crea el endpoint Gateway de S3 `tlc-s3-endpoint` "para que Glue dentro de la VPC llegue a S3" (`:8`, `:115-138`).
  - Ninguno de los dos se usa: Glue JDBC se descartó en el Punto 3 (`punto3-ingesta/README.md:22,26`).
- `punto2-fuentes/infra/destruir_infra.py:41-127` borra la EC2, la RDS, el subnet group, los endpoints, los SG, los parámetros SSM y, con `--incluir-bucket`, el bucket. No toca la Lambda ni la regla, y nada de Glue.
- `punto4-preparacion/README.md:1-3`: solo el título y "**Pendiente.** Limpieza y tipado de los datos con AWS Glue y Apache Spark."

### Referencia de patrones: `JeanArdila711/fundamentals-dataengineering` (solo referencia, convención "Pipeline nuevo")

`m4-raw-to-structured/raw_to_structured.py` es un Glue job en PySpark:
- Argumentos `--dataset --ds --bucket --raw_prefix --structured_prefix` por `getResolvedOptions` (`:21-33`).
- Una corrida procesa una partición mensual y la reemplaza (`:7-9`, `:38-39`).
- Esquema canónico en un dict `TIPOS`: castea cada columna y falla si falta alguna (`:54-100`, `:130-134`).
- Agrega `file_name` con `input_file_name()` (`:119-121`) y falla si la entrada viene vacía (`:123-126`).
- Deriva `trip_date` porque los viajes no coinciden con el mes de la partición, además de `pickup_hour`, `trip_duration_minutes` y `avg_speed_mph` con guarda en duración 0 (`:140-156`).
- Pasa los nombres de columna a minúsculas (`:102-104`, `:158-161`).
- Escribe con `coalesce(1)` y `mode("overwrite")` en `structured/{dataset}/ds=.../` (`:163-170`).
- Relee lo escrito y compara el conteo (`:172-178`).
- No filtra filas ni marca calidad.

En `m3-airflow-orchestration/dags/tlc_data_lake.py`:
- Lanza el job con `GlueJobOperator` (`:94-110`).
- Registra la partición con DDL de Athena (`ALTER TABLE ... ADD IF NOT EXISTS PARTITION`) y no usa crawler (`:113-127`).

`m4-landing-to-raw/lambda_function.py:35-319` tiene un contrato de esquema con pyarrow leído desde el footer y manda lo que falla a `quarantine/`. Este proyecto no tiene zona landing.

### AWS Glue, Step Functions y Academy (cuenta de Jean, lecturas del 2026-11-15)

**Estado de la cuenta:**
- `glue get-jobs`, `get-databases` y `get-crawlers` vienen vacíos. `stepfunctions list-state-machines` también.
- S3 tiene solo `codigo/` y `raw/`.

**LabRole:**
- `MaxSessionDuration` es de 3600 s.
- La trust policy incluye `glue.amazonaws.com`, `states.amazonaws.com`, `lambda.amazonaws.com` y `elasticmapreduce.amazonaws.com`.
- Las políticas `VocLabPolicy1/2/3` no se pueden leer (`iam get-policy` da AccessDenied por un deny explícito de `Pvoclabs1`). Qué acciones de Glue y Step Functions permite solo se sabe probando.

**Documentación de AWS** (consultada el 2026-11-15):
- Versiones (https://docs.aws.amazon.com/glue/latest/dg/release-notes.html):

  | Glue | Spark | Python |
  |---|---|---|
  | 4.0 | 3.3.0 | 3.10 |
  | 5.0 | 3.5.4 | 3.11 |
  | 5.1 | 3.5.6 | 3.11 |
  | 6.0 | 4.1.1 | 3.13 |

  Un job creado sin `GlueVersion` queda en 6.0, y en Academy solo se probó 5.0.
- Workers (https://docs.aws.amazon.com/glue/latest/dg/add-job.html):
  - 1 DPU = 4 vCPU y 16 GB.
  - G.1X = 1 DPU y G.2X = 2 DPU.
  - G.025X es solo para jobs de streaming.
  - Flex está disponible para G.1X y G.2X.
  - La concurrencia máxima por job es 1 por defecto.
  - Timeout por defecto de 480 min en Glue 5.0 o superior.
- Job bookmarks (https://docs.aws.amazon.com/glue/latest/dg/monitor-continuations.html):
  - Para S3 se basan en el *last modified time*: un archivo reescrito se reprocesa.
  - Requieren `transformation_ctx`, `job.init` y `job.commit`.
  - Un reset no limpia los destinos.
  - La documentación está escrita para DynamicFrames.
- Step Functions (https://docs.aws.amazon.com/step-functions/latest/dg/connect-glue.html):
  - Hay integración optimizada `arn:aws:states:::glue:startJobRun.sync`.
  - Necesita `glue:StartJobRun`, `GetJobRun`, `GetJobRuns` y `BatchStopJobRun`.

## Conexiones y flujo de datos

1. **Fuentes → raw (Punto 3):** RDS (green, zonas), EC2 (yellow) y la URL de la TLC (HVFHV) → `raw/` en S3. Cada mes es un archivo con un nombre determinista, y reingerir un mes sobrescribe esa clave (`punto3-ingesta/ec2_ingesta.py:97-144`, `lambda_ingesta.py:64-69`).
2. **raw → trusted (Punto 4):** no existe. No hay código, recursos ni prefijo.
3. **trusted → catálogo → consultas (Puntos 5 a 7):** Glue Data Catalog y Hive, y después Athena, SparkSQL y PySpark. Tampoco existe todavía.
4. **Encadenamiento:** la convención "Ingesta automática" deja Step Functions para encadenar los Puntos 4 y 5 "cuando se llegue ahí". Hoy solo EventBridge dispara la ingesta.

## Patrones y convenciones existentes

- **Recursos idempotentes:** se buscan por nombre o etiqueta, se crean o actualizan, y se esperan con waiters. Todos llevan la etiqueta `Project`, y no hay archivos de estado.
- **Código en S3:** se publica en `codigo/<punto>/`, fuera de las zonas del datalake (`comun/config.py:37`).
- **Errores:**
  - Se capturan excepciones específicas (`S3UploadFailedError`, `ClientError`, `pymysql.MySQLError`).
  - Los errores se acumulan en una lista y el proceso termina con `sys.exit(1)` o `RuntimeError(json)`.
  - El resumen se imprime en JSON y queda en CloudWatch.
- **Escritura en S3:** un objeto por mes con clave determinista. Se verifica después de subir (tamaño o filas) y lleva metadatos de usuario (`filas`, `cargado-en`, `huella`). No hay escritura en un prefijo temporal con renombrado posterior.
- **Exclusión:** una sola corrida a la vez (concurrencia 1 y `flock`), y el reintento es la corrida siguiente (ruling de `punto3-ingesta`).
- **Tests:** un `test_*.py` con asserts sueltos y `print("ok")`, sin pytest (`punto3-ingesta/test_raw.py`).
- **Cada script de punto:** agrega la raíz al `sys.path` para hacer `from comun import config` (`desplegar.py:24`).
- **README de cada punto:** diagrama, "Por qué así" con lo descartado, la zona, idempotencia, tabla de archivos, Reproducir, Evidencias y Resultados (`punto3-ingesta/README.md`).

## Vacíos

- **Permisos reales de LabRole** para `glue:CreateJob`, `StartJobRun` y `CreateDatabase` y para `states:CreateStateMachine`: no se pueden leer, se descubren probando.
- **Límites de Glue en Academy:** máximo de workers o DPU concurrentes y versiones aceptadas fuera de 5.0. No se verificaron.
- **Precio por DPU-hora de Glue:** sin verificar, porque la consulta a la página de precios se cortó.
- **Mínimo de workers por job:** sin verificar en la documentación.
- **`spark.sql.sources.partitionOverwriteMode=dynamic` en Glue:** no se verificó cómo se configura ni qué advertencias tiene.
- **Si los job bookmarks funcionan con `spark.read`** y no solo con DynamicFrames: sin verificar.
- **Cuántas filas caen fuera del mes del archivo:** solo se midieron los extremos. Yellow y HVFHV de 2024-01 a 2024-07 no traen estadísticas.
- **Si las esperas negativas, los viajes fuera de mes y `driver_pay > base_passenger_fare` se filtran o se marcan:** no está decidido (`findings.md:23-27` deja las dos opciones).
- **P2 y P3**, que definen qué columnas de tarifa se derivan, siguen en Proposed.

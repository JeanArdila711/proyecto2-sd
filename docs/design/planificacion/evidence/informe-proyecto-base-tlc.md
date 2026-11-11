> **Origen:** informe N3 de un subagente (explorador), 2026-11-10, sobre las notas del vault del curso Fundamentos Data Engineering (P1, P2, P3 Decisiones Técnicas y las secciones TLC de M2, M3 y M4). Al importarlo se reemplazó el ID de la cuenta AWS personal por `<cuenta-personal>` porque este repo es público; el resto es literal.

# Informe: notas del vault sobre el pipeline TLC (Fundamentos Data Engineering)

Fuentes leídas (MCP Obsidian, solo lectura), todas bajo `02 - Aprendizaje Independiente/Cursos/Fundamentos Data Engineering/`:
- `Proyecto 1 - Decisiones Técnicas.md` (P1, completa; frontmatter `estado: en-progreso`)
- `Proyecto 2 - Decisiones Técnicas.md` (P2, completa; `estado: completado`)
- `Proyecto 3 - Decisiones Técnicas.md` (P3, completa; `estado: completado`)
- `M2 - Ingesta de Datos.md`, sección "🚕 E4 — Proyecto 1: TLC Pipeline — Parte 1" (brief P1)
- `M3 - Orquestamiento de Datos.md`, sección "🚕 E5 — Proyecto 2: TLC Pipeline — Parte 2" (brief P2)
- `M4 - Data Lakes.md`, sección "🚕 E5 — Proyecto 3: TLC Pipeline — Parte 3" (brief P3)
- `Conceptos para los Proyectos.md`: no se leyó (ninguna nota lo exigía para entender lo anterior).

Notas relacionadas no leídas enteras:
- `03 - Universidad/Semestre 8/Tópicos Especiales en Telemática/Proyecto 2/Proyecto 2 - Big Data TLC.md`: es la nota de la materia SI3007 (backlink desde P1, P2 y P3). Tags `entrega, telemática, big-data, tlc-pipeline, proyecto2`, `estado: en-progreso`. Headings: Conexiones, Datos clave, Rúbrica (Requerimientos, Entregables), Notas del proyecto. Solo se vio el mapa de headings.
- No existe "Proyecto 4" ni un M5 que continúe TLC en el listado de la carpeta. Hay `M5 - Data Warehouses y Modelado de Datos.md`, `M6 - Pipeline de datos modernos.md`, `M7 - El Futuro de Data Engineering.md`, pero no se abrieron y no se verificó si usan TLC. La búsqueda de `tlc-pipeline` solo devuelve P1, P2, P3 y la nota universitaria.
- Repo del proyecto base citado en las notas: `~/Developer/Proyectos/personales/fundamentals-dataengineering` (P1, P3) y subcarpeta `m3-airflow-orchestration` (P2, P3). Directorios mencionados: `m3-airflow-orchestration/dags/`, `m4-landing-to-raw/lambda_function.py`, `m4-raw-to-structured/raw_to_structured.py`. El directorio de la Lambda de M2 no tiene nombre explícito (sí `test_lambda_function.py`).

---

## 1. Arquitectura final que quedó

Diagrama (P3, sección "La arquitectura que quedó"):

```
TLC (CloudFront)
  │  Lambda tlc-ingestion
  ▼
landing/yellow_tripdata/2025/yellow_tripdata_2025-01.parquet
  │  Lambda tlc-landing-to-raw  -- contrato incumplido --> quarantine/.../ds=2024-01-01/
  ▼
raw/yellow_tripdata/ds=2025-01-01/
  │  Glue Job tlc-raw-to-structured (Spark)
  ▼
structured/yellow_tripdata/ds=2025-01-01/
  │  ALTER TABLE ADD PARTITION (Athena)
  ▼
Glue Catalog -> tlc_data_lake.yellow_tripdata -> consultable
```
Orquestación: Airflow 3.3.0 local en Docker Compose (no en AWS) invoca las Lambdas, el Glue Job y el DDL de Athena. DAG `tlc_data_lake`: `start → ingest → promote_to_raw → raw_to_structured → register_partition → end`. DAG previo `tlc_ingestion` (solo ingesta, yellow+green).

### Recursos AWS (nombres exactos)

| Recurso | Valor | Fuente |
|---|---|---|
| Cuenta AWS | `<cuenta-personal>` (alias `jeanardila711`), **Free plan**: $100 de crédito inicial, hasta Feb 11 2027, sin cargos salvo upgrade | P1 "Recursos creados", "Free plan en vez de Paid" |
| Región | `us-east-2` (Ohio) | P1, ARN en P2 |
| Usuario de trabajo | `admin-engineer` (`AdministratorAccess` + `IAMUserChangePassword`, con MFA). Sin access keys | P1 |
| Usuario de Airflow | `airflow-invoker`, sin consola, política `invoke-tlc-ingestion` (`lambda:InvokeFunction` sobre `arn:aws:lambda:us-east-2:<cuenta-personal>:function:tlc-ingestion`); P3 dice que luego puede correr el Glue Job y tocar la tabla, "nombrados por ARN" (la política ampliada no se transcribe) | P2, P3 "IAM" |
| Bucket | `jean-ardila-data-lake` (namespace global) | P1 |
| Prefijos | `landing/`, `raw/`, `structured/`, `quarantine/`; además se mencionan `athena-results/` (P3 pendientes) y `scripts/raw_to_structured.py` (P3 pendientes, como destino deseado) | P1, P3 |
| Keys | landing: `landing/{dataset}/{year}/{archivo}.parquet`; raw: `raw/yellow_tripdata/ds=YYYY-MM-01/`; structured: `structured/yellow_tripdata/ds=YYYY-MM-01/`; quarantine: `quarantine/yellow_tripdata/ds=2024-01-01/` | P1, P3 |
| Lambda ingesta | `tlc-ingestion`, Python 3.14, 512 MB, timeout 2 min; variables de entorno `BUCKET_NAME`, `SOURCE_BASE_URL` (obligatorias), `LANDING_PREFIX` (con default). Un solo archivo `.py`, usa `urllib3` + `boto3` del runtime | P1 |
| Rol de esa Lambda | `tlc-ingestion-role-mmc2xmvx`; política inline `s3-write-data-lake` (`s3:PutObject`, `s3:AbortMultipartUpload`, `s3:ListMultipartUploadParts` sobre `arn:aws:s3:::jean-ardila-data-lake/*`) | P1 |
| Lambda promoción | `tlc-landing-to-raw`, Python 3.13, usa la layer AWSSDKPandas (pyarrow sin S3FileSystem ni zstd). Sin `s3:DeleteObject`. Memoria/timeout no aparecen (se midió 147 MB usados) | P3 |
| Glue Job | `tlc-raw-to-structured`, Spark, 2 x G.1X, timeout 20 min, retries 0, job bookmarks Disable. Versión de Glue/Spark: no aparece | P3 |
| Glue Crawler | `tlc-structured-crawler` (solo descubrimiento inicial del esquema) | P3 |
| Glue Database | `tlc_data_lake` | P3 |
| Tabla | `tlc_data_lake.yellow_tripdata` (el brief sugería `yellow_trips`) | P3 |
| Rol IAM Glue | `tlc-glue-role`; `DeleteObject` solo en `structured/`; necesitó `s3:GetObject` sobre `structured/*` y `glue:GetJob` (esta última era del usuario de Airflow) | P3 "IAM" |
| Presupuesto | `My Zero-Spend Budget`, alerta desde 0,01 USD | P1 |
| Airflow | `apache/airflow:3.3.0`, `postgres:16`, `redis:7.2-bookworm`; 7 contenedores; UI `http://localhost:8080`; provider `apache-airflow-providers-amazon` 9.31.0; operador `LambdaInvokeFunctionOperator` (`airflow.providers.amazon.aws.operators.lambda_function`); conexión `aws_default` cifrada con Fernet | P2 |
| Runtime de laptop | Mac, `AIRFLOW_UID=501` | P2 |

Workers: el handler de ingesta no conoce los datasets; el evento es `{"dataset": "yellow_tripdata", "date": "2025-01"}` y arma `{SOURCE_BASE_URL}/yellow_tripdata_2025-01.parquet`. Fuente: `https://d37ci6vzurychx.cloudfront.net/trip-data/{DATASET_NAME}_YYYY-MM.parquet` (brief M2).

## 2. Datos

- **Datasets**: brief limita a Yellow y Green (M2 E4 "Alcance"). Yellow: 2025 completo (12 meses) hasta structured. Green: ingestado a `landing/` para los 12 meses de 2025 (P2 backfill: 24 ingestas = 2 datasets x 12 meses), pero **no** pasó por raw/structured ni tiene tabla (P3 pendiente: "Extender a green: necesita su propia tabla en el catálogo y su propio crawler").
- **2024**: solo `yellow_tripdata_2024-01` se procesó, para disparar quarantine.
- **Tamaño**: 805,3 MB en 24 archivos en S3 (P2). `yellow_tripdata_2025-01.parquet` = 59.158.238 bytes (~56 MB; 56,4 MB en P3). Partición mensual ~60 MB.
- **Filas** (verificado en Athena, P3): 12 particiones, **48.722.602** filas, rango `2025-01-01` → `2025-12-01`, sin huecos.

| Mes | Filas | Mes | Filas |
|---|---|---|---|
| 2025-01 | 3.475.226 | 2025-07 | 3.898.963 |
| 2025-02 | 3.577.543 | 2025-08 | 3.574.091 |
| 2025-03 | 4.145.257 | 2025-09 | 4.251.015 |
| 2025-04 | 3.970.553 | 2025-10 | 4.428.699 |
| 2025-05 | 4.591.845 | 2025-11 | 4.181.444 |
| 2025-06 | 4.322.960 | 2025-12 | 4.305.006 |

- **Formato**: Parquet (compresión zstd en origen; P3). structured en Parquet con `coalesce(1)` por partición.
- **Particionado**: mensual por `ds` (fecha lógica = mes del archivo, formato `YYYY-MM-01`), no por fecha de viaje ni diario (ver sección 4).
- **Esquema** (lo que dicen las notas, no hay listado completo de columnas):
  - Tres esquemas yellow: 2023-01 con `airport_fee` en minúscula; 2023-07..2024-12 con `Airport_fee`; 2025-* con `Airport_fee` + `cbd_congestion_fee`.
  - El worker de 2024-01 volcó 19 columnas observadas; falta `cbd_congestion_fee`. Inferencia: 2025 tiene 20 columnas (las notas no lo dicen explícito).
  - Columna `VendorID` mencionada; el Glue Job pasa **todos los nombres a minúscula**.
  - Añadidas en raw (según brief): `ds` y `file_name`. Según P3, `file_name` se agrega en el Glue Job con `input_file_name()`, no en la Lambda. Derivadas en structured: `trip_date`, `pickup_hour`, `trip_duration_minutes`, `avg_speed_mph`.
  - Tipos canónicos declarados en el job (fechas `date`, timestamps `timestamp`, numéricas `double/int/bigint`); la lista exacta de tipos no aparece.
- **Calidad**: un archivo mensual contiene viajes de meses vecinos (enero: 21 viajes del 2024-12-31 y 1 del 2025-02-01). Velocidades imposibles (promedio 414,6 mph a las 5 h; mediana 16,1 mph); se dejan crudos en structured, el filtrado correspondería a una capa `analytics` no construida.

## 3. Estado actual

- **AWS (desplegado, persistente)**: bucket `jean-ardila-data-lake` con datos 2025 (landing yellow+green; raw/structured solo yellow), 2 Lambdas, Glue Job, Crawler, Database, tabla, roles, presupuesto cero. Nada se dice de haberlos borrado. No se verificó el estado real de la cuenta (solo vault).
- **Airflow local**: **apagado** desde el 2026-08-19 (`docker compose down`; P3 "Estado del entorno"). Volumen de Postgres conservado (conexión `aws_default` cifrada, usuario UI `airflow`, historial). Ambos DAGs (`tlc_ingestion`, `tlc_data_lake`) **pausados a propósito**: activos generan una corrida roja cada mes porque el TLC publica con meses de rezago; solución diferida = sensor que espere al archivo.
- **Para retomar**:
  ```
  cd ~/Developer/Proyectos/personales/fundamentals-dataengineering/m3-airflow-orchestration
  docker compose up -d
  ```
  Tarda ~1 min; UI en `http://localhost:8080`. **No** correr `airflow-init`. `docker compose down` conserva la BD; `down -v` borra credenciales y obliga a rehacer `airflow-init`; `docker system prune -a` libera ~4 GB de imágenes. La llave Fernet vive en `.env` (en `.gitignore`); si se pierde hay que recrear conexiones. Probar la conexión con el botón *Test*.
- **Costos mencionados** (P3): Glue ETL $0,44/DPU-hora (mín. 1 min, mín. 2 DPU) ≈ 15 corridas x ~$0,03 ≈ $0,45; Crawler 1 corrida $0,05 (sin verificar contra factura); Data Catalog $0; Athena $5/TB, mín. 10 MB/query, DDL gratis; Lambda en free tier. "Total del módulo: menos de $1 de los créditos". Corrida de Glue fallida por permisos: 0,048 DPU-h ≈ $0,02. Job zombie con timeout default (480 min) ≈ $7.
- **Crédito**: $100 hasta Feb 11 2027. Hoy es 2026-11-10: quedan ~3 meses (cálculo mío, no de las notas).
- **Git**: commits citados `c8368cf` (run_backfill.sh, borrado, solo historial), `88d5be5` (M3), `49ad713`, `39b4e21`, `c6be94b` (P3), más dos fixes sin hash. Push a GitHub figura pendiente en P1 y P2; las notas no confirman que se haya hecho.

## 4. Decisiones técnicas y lecciones

1. **Streaming HTTP → S3 sin disco** (`upload_fileobj` sobre respuesta file-like). Memoria máx. 144 MB de 512 con un parquet de 56 MB.
2. **`urllib3` + `Retry(total=5, backoff_factor=1, status_forcelist=[429,500,502,503,504])`**, métodos GET/HEAD. Reintento de transporte en Lambda, de tarea en Airflow. 403 no se reintenta (92 ms).
3. **Falla lanzando excepción, nunca `return {"statusCode": 500}`**: Lambda solo marca error si lanza; Airflow `LambdaInvokeFunctionOperator` lanza `ValueError` solo si la respuesta trae `FunctionError`. Si no, DAG verde con pipeline roto. La solución del instructor devolvía 500 y además tenía `UnboundLocalError` en el `except ClientError`.
4. **Worker paramétrico** (`dataset` + `date` en `YYYY-MM`, validación con regex `^[a-z0-9_]+$` y `^(\d{4})-(0[1-9]|1[0-2])$` contra path traversal). Sin `url` explícita en el evento.
5. **Sin access keys en Lambda** (rol de ejecución); en cambio `airflow-invoker` sí lleva access keys porque Airflow corre fuera de AWS.
6. **Sin `head_object` post-subida**: requiere `s3:GetObject`; el rol queda mínimo.
7. **Free plan + presupuesto de gasto cero** (alerta desde 0,01 USD).
8. **Fernet key**: el compose oficial no trae `FERNET_KEY`; Airflow cae a `NullFernet` y la conexión `aws_default` quedaba en texto plano (`is_encrypted = f`). Fix: generar la llave al `.env`, recrear contenedores y re-cifrar con `c.password = c.password`. La llave mide 44 caracteres (una de 43 falla).
9. **`@monthly` en Airflow 3 devuelve el mes equivocado** (bug no trivial, no está en el curso): el preset construye `CronTriggerTimetable` sin intervalo de datos, así `data_interval_start` = instante del disparo. La corrida del 1 ago 2026 pidió `2026-08`. Fix: `schedule=CronDataIntervalTimetable("0 0 1 * *", timezone="UTC")` (`airflow.timetables.interval`). Mantenido en `tlc_data_lake`.
10. **Nombres que cambiaron en Airflow 3 / provider 9.31.0**: operador `LambdaInvokeFunctionOperator` (no `AwsLambdaInvokeFunctionOperator`); imports `airflow.sdk.DAG`; backfill = `airflow backfill create --dag-id ... --from-date 2025-01-01 --to-date 2025-12-01 --max-active-runs 1` (con `--dry-run`, `--reprocess-behavior none`).
11. **Un solo DAG con `.expand()`** sobre `DATASETS` (Jinja se renderiza en payload expandido); `catchup=False` explícito, `max_active_runs=1`, `retries=2`, `retry_delay=2 min`, backoff exponencial, `execution_timeout=10 min`, `dagrun_timeout=1 h`, invocación `RequestResponse`.
12. **Compose oficial modificado en 2 líneas**: línea 76 (`_PIP_ADDITIONAL_REQUIREMENTS` con provider amazon) y `AIRFLOW__CORE__LOAD_EXAMPLES: 'false'`. Para producción se hornearía una imagen propia.
13. **Política del brief M3 con basura del instructor**: `sts:AssumeRole` sobre account `<cuenta-instructor>` y `ROLE_NAME` sin reemplazar; se omitió. La política "Glue" del brief usa `Resource` placeholder.
14. **Partición mensual, no diaria** (800 MB / 365 ≈ 2 MB por partición). Corrección posterior marcada ✳️ (2026-10-26): ni 60 MB está por encima de los mínimos oficiales de Databricks (≥1 GB) o BigQuery (~10 GB); mensual se mantiene como ejercicio.
15. **Clave de partición = fecha lógica (`ds`), no fecha de viaje**: los archivos mensuales contienen viajes de otros meses; con `overwrite` por fecha de viaje se perderían filas en silencio (ej. las 21 filas del 31-dic). `trip_date` queda como columna derivada. Un open table format (Iceberg/Delta/Hudi) resolvería esto con MERGE.
16. **`landing` no se borra**: se prefiere lifecycle policy 7-30 días (el brief pedía borrar). Pendiente aplicarla.
17. **`ALTER TABLE ... ADD PARTITION IF NOT EXISTS` en vez de crawler por corrida**: medido crawler 40 s/$0,05 vs ADD PARTITION 1,7 s-251,9 s/$0. Nota ✳️ posterior: el argumento correcto no es velocidad sino determinismo, costo mínimo del crawler y riesgo de reescribir esquema.
18. **Lambda `landing→raw` copia (`copy_object`), no reescribe**: la layer AWSSDKPandas trae pyarrow sin `S3FileSystem` (`ImportError`) y sin codec zstd (`ArrowNotImplementedError`). Valida solo el footer (64 KB de 56,4 MB) con range requests de boto3. Tres chequeos: abre como parquet, esquema 2025 por nombre y tipo, suma de row groups = filas del footer. Pérdida asumida: páginas corruptas con footer sano revientan después en Glue.
19. **Quarantine falla la invocación igual** (`QuarantinedError`) para no dejar hueco silencioso. Tensión documentada: el brief pide cuarentenar 2024-01 (columna nueva legítima); la política real sería aceptar columnas nullables nuevas.
20. **Glue Job**: `coalesce(1)`, verificación releyendo desde S3, timeout 20 min (default 480), retries 0 (los gestiona Airflow; multiplicar da 2x3=6 corridas), job bookmarks off (rompen idempotencia). Nombres a minúscula.
21. **IAM mínimo, errores en runtime**: escribir y releer son permisos distintos (`s3:GetObject` en `structured/*`); correr un job y leer su definición también (`glue:GetJob`). Un fallo en 0,7 s casi siempre es permisos.
22. **Calidad estadística**: con duraciones raras, filtrar no arregló el promedio; cambiar a mediana sí. Los viajes imposibles quedan crudos en structured.
23. **Mediciones del backfill P3**: 33,7 min para 12 meses; `raw_to_structured` prom. 99,8 s (28,0-113,2); `register_partition` prom. 56,8 s (1,7-251,9); `ingest` 3,0 s; `promote_to_raw` 2,0 s. Athena DDL muy variable (cola compartida).

## 5. Cobertura de la rúbrica SI3007

| # | Punto | Cobertura | Evidencia en las notas |
|---|---|---|---|
| 1 | Caso de estudio con >=5 preguntas de negocio | **Nada** | No aparecen preguntas de negocio. Solo consultas exploratorias de calidad (velocidad por hora, viajes por `trip_date`, conteo por `ds`) en P3 "Calidad de datos". |
| 2 | Fuentes simuladas: RDS MariaDB + archivos en EC2 + URLs | **Parcial** (solo URLs) | URL pública TLC en CloudFront (M2 brief, `d37ci6vzurychx.cloudfront.net`). RDS, MariaDB, EC2: no aparecen. |
| 3 | Ingesta automática al datalake en S3, en zonas correctas | **Parcial/Cubierto con reservas** | Lambda `tlc-ingestion` + DAG Airflow con backfill 2025 (24/24 verdes) escribe en `landing/`; zonas landing/raw/structured/quarantine con promoción automática (P3). Reservas: Airflow corre en Docker local (apagado, DAGs pausados), no es "automática" sin intervención; solo fuente URL (no RDS ni EC2). Nomenclatura de zonas difiere de raw/trusted de la rúbrica. |
| 4 | raw→trusted con Glue + Spark | **Cubierto** (yellow) | Glue Job `tlc-raw-to-structured` Spark 2xG.1X: tipado, derivadas, partición `ds`, escritura Parquet (P3). Green no pasó por esta etapa. `structured` es el equivalente a trusted/silver (equivalencia mía). |
| 5 | Catalogación con Glue y EMR/Hive | **Parcial** (Glue sí, EMR/Hive no) | Database `tlc_data_lake`, tabla `yellow_tripdata`, crawler `tlc-structured-crawler`, particiones por `ADD PARTITION`. EMR/Hive: no aparece. |
| 6 | SQL descriptivo con Athena, EMR/Hive y SparkSQL | **Parcial** (Athena puntual) | Consultas Athena ad hoc (conteos, min/max `ds`, velocidad por hora con mediana) en P3. No hay un set de queries guardado, ni Hive, ni SparkSQL. |
| 7 | Analítica descriptiva con PySpark | **Nada** | El Glue Job es ETL (Spark), no analítica descriptiva. No aparece notebook ni script de análisis. Que el job use PySpark no se dice textualmente; el script es `raw_to_structured.py` y usa `input_file_name()`. |
| 8 | Visualización + Streamlit vía API Gateway | **Nada** | No aparecen matplotlib/Dash/PowerBI/Grafana, Streamlit ni API Gateway. (P1 menciona API Gateway solo para descartar la forma `statusCode/body`.) |
| — | Repo GitHub con directorio por punto + instrucciones | **Parcial** | Repo con carpetas `m3-airflow-orchestration`, `m4-landing-to-raw`, `m4-raw-to-structured`; instrucciones de levantar Airflow en P2/P3. Push a GitHub figura pendiente (P1, P2). Estructura por módulo, no por punto de la rúbrica. |

## 6. Huecos y riesgos para adaptarlo

- **AWS Academy vs. cuenta personal**: las notas solo hablan de cuenta personal con Free plan (`<cuenta-personal>`, `us-east-2`). Academy/Learner Lab no aparece. Si SI3007 exige Academy: restricciones típicas (roles preexistentes, no crear usuarios IAM) pueden chocar con `airflow-invoker`, `tlc-glue-role` y las políticas creadas a mano. No verificado desde las notas; confirmar con el enunciado.
- **Free plan limita a "select services"** (P1). Las notas dejan abierto si Glue y Athena entran (P1, P2, P3 pendientes), pero P3 reporta que corrieron con costo < $1 de los créditos, lo que sugiere que sí. EMR, RDS, EC2 y API Gateway no fueron verificados contra el Free plan; EMR y RDS suelen ser servicios no gratuitos. Ojo con costos EMR frente a los $100 que vencen Feb 11 2027.
- **Servicios no usados y requeridos por la rúbrica**: RDS MariaDB, EC2 con archivos, EMR, Hive, SparkSQL, PySpark analítico, API Gateway, Streamlit, herramienta de viz, preguntas de negocio. Ninguno tiene antecedente en las notas.
- **Fuentes**: el pipeline asume una única fuente HTTP. Hay que decidir qué datos van a RDS y a EC2 (el TLC tiene yellow, green, FHV, HVFHV; solo yellow/green se tocaron). Green no está catalogado.
- **Ingesta "automática"**: el orquestador es local y está pausado; la rúbrica pide ingesta automática. Considerar que Airflow en Docker dentro del Mac no es un servicio AWS. Otras piezas del brief: sensor no resuelto, DAG pausado, rezago de publicación del TLC.
- **Nombres de zonas**: las notas usan landing/raw/structured/quarantine; la rúbrica habla de raw→trusted. Hay que decidir el mapeo (o renombrar, lo que toca prefijos, Lambdas, job y tabla).
- **Datos sin limpiar en structured**: viajes imposibles, viajes fuera de mes. Las preguntas de negocio de la rúbrica probablemente necesiten la capa `analytics` que P3 deja fuera de alcance.
- **Esquema de partición**: mensual ~60 MB, por debajo de mínimos oficiales (nota ✳️ P3). Para Hive/EMR conviene decidir si se mantiene `ds=YYYY-MM-01`.
- **Dependencias frágiles**: layer AWSSDKPandas sin S3FileSystem/zstd (la Lambda de promoción solo copia); `scripts/raw_to_structured.py` no versionado en S3 (el job lee del bucket de assets de Glue; actualizar exige re-subir por consola); Fernet key en `.env` local.
- **Seguridad**: la sección "2. Crea tu cuenta en AWS" del brief en `M2 - Ingesta de Datos.md` contiene usuario y contraseña de `admin-engineer` en texto plano. No se reproduce aquí. Recomendación: rotarla y borrarla de la nota, sobre todo antes de compartir el vault o el repo. Además, las access keys de `airflow-invoker` están en el volumen de Postgres local.
- **Inconsistencias entre notas**: P1 `estado: en-progreso` con pendientes que P2/P3 ya superaron; P2 sigue listando "Push del commit 88d5be5". No se sabe si el repo está en GitHub.
- **Versión/identificadores a revalidar**: runtimes Python 3.13/3.14, Airflow 3.3.0, provider 9.31.0 y valores de Free plan son de ago-oct 2026; revisar contra la consola antes de reutilizar.
- **Reutilización de credenciales/ARNs**: el account ID, ARNs y bucket están fijos en las notas; para un entorno nuevo (cuenta de equipo/Academy) hay que reemplazarlos.

## 7. Pendientes que las notas dejaron abiertos

De P1:
- Subir el repo a GitHub.
- Capas opcionales: Docker, GitHub Actions, Terraform.
- (Los de "DAG de Airflow" y "variables de entorno/invocar" ya se cerraron en P2/P1; el de verificar Glue/Athena en Free plan sigue sin respuesta escrita.)

De P2:
- Push del commit `88d5be5` a GitHub.
- Capas opcionales: imagen propia de Docker, GitHub Actions, Terraform.
- Verificar Glue y Athena en Free plan antes de M4 (sin respuesta explícita).
- Decisión abierta: sensor que espere a que el TLC publique el mes si se quiere dejar el DAG activo.
- Bajar el entorno con `docker compose down` al terminar cada sesión.

De P3:
- Lifecycle policy en `landing/` (30 días) y `athena-results/` (7 días).
- Extender a green: tabla y crawler propios, no solo otra corrida del DAG.
- Repuntar el Glue Job a `s3://jean-ardila-data-lake/scripts/raw_to_structured.py` si el *Script path* es editable.
- Capas opcionales acumuladas: Docker propio, GitHub Actions, Terraform.
- Bajar el entorno de Airflow.
- Costo del crawler ($0,05) sin verificar contra factura (nota ✳️).
- Brief M4 marca "Diagrama de la arquitectura final" como `todo` pendiente (también el de M2).
- Capa `analytics` (reglas de negocio para viajes válidos), explícitamente fuera del alcance de M4.

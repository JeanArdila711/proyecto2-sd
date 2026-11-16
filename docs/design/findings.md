# Proyecto 2 Big Data TLC — Findings

Hechos durables que sirven a otros topics. Un bloque por finding, solo con contraste reutilizable: algo que costó descubrir o que se hizo de dos formas con resultados distintos. Se carga solo cuando la tarea toca un tema listado acá. Pasadas unas 150 líneas, se parte en `findings/{tema}.md`.

## [hecho] Esquema: `cbd_congestion_fee` no existe en los archivos de 2024

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** la columna aparece desde 2025 (el cobro arranca el 5 de enero de 2025) en yellow, green y HVFHV. En 2024 está ausente, no en null. Cualquier contrato de esquema, ingesta o tabla que cubra los dos años tiene que tolerar la columna faltante.
- **Provenance:** footers de `{yellow,green,fhvhv}_tripdata_2024-06` y `2025-06` leídos por range request; texto de la página de datos de la TLC.

## [hecho] HVFHV: en 2024–2025 solo hay Uber (HV0003) y Lyft (HV0005)

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** conteo completo de `hvfhs_license_num`: 2024-01 → Uber 14,43 M, Lyft 5,23 M; 2025-12 → Uber 15,97 M, Lyft 6,13 M. Via (HV0004) y Juno (HV0002), que lista el diccionario, ya no aparecen. Lo que se modele por compañía tiene dos valores.
- **Provenance:** lectura de la columna en `fhvhv_tripdata_2024-01` y `2025-12` (sesión 2026-11-10).

## [hecho] Propinas: `tip_amount` solo registra las pagadas con tarjeta

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** según el diccionario de yellow (2025-03-18), las propinas en efectivo no se registran. Todo análisis de propinas en taxis se filtra a `payment_type = 1`; promediar sobre todos los pagos subestima la propina.
- **Provenance:** `data_dictionary_trip_records_yellow.pdf`.

## [hecho] Calidad HVFHV: esperas negativas y pagos al conductor mayores que la tarifa base

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** en el row group 0 de junio, entre 2.451 y 6.636 viajes por compañía tienen `pickup_datetime < request_datetime`. Además, `driver_pay > base_passenger_fare` en ≈ 12–16 % de los viajes de Uber y ≈ 7–8 % de los de Lyft. La capa trusted tiene que filtrar o marcar las esperas negativas, y la comparación `driver_pay / base_passenger_fare` puede dar más de 100 %.
- **Provenance:** row group 0 de `fhvhv_tripdata_2024-06` y `2025-06` (sesión 2026-11-10).

## [hecho] Volumen: HVFHV es el 88 % de los datos

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** de 12,38 GiB en 72 archivos (2024–2025), HVFHV ocupa 10,93 GiB, con archivos de hasta 511 MiB (unos 20 M de filas al mes). Yellow pesa 1,42 GiB y green unos 13 MiB. El dimensionamiento (timeouts de ingesta, workers de Glue o EMR) lo define HVFHV.
- **Provenance:** `HEAD` a los 72 archivos en CloudFront (sesión 2026-11-10).

## [hecho] AWS Academy: límites de tamaño por servicio en Learner Lab

- **Date:** 2026-11-11 · **Source topic:** `planificacion`
- **Finding:** solo `us-east-1` y `us-west-2`. EC2 hasta `t3.large` / `m5.large` / `c5.large` (ningún `xlarge`). RDS MariaDB `db.t3.micro`–`db.t3.medium`, Multi-AZ y ≥ 101 GB permitidos; `db.t3.large` y `db.m5.large` denegados. Lambda con `LabRole` acepta 3008 MB, 900 s y 10 GB de `/tmp`. Glue acepta jobs `G.1X` × 10 con Glue 5.0. EMR acepta en la API `m5.xlarge` / `m5.2xlarge` con Hive y Spark (`emr-7.14.0`), sin verificar que lance las máquinas.
- **Provenance:** sesión 2026-11-11: `run-instances --dry-run` por tipo, `create-db-instance` con contraseña inválida, recursos de prueba creados y borrados.

## [hecho] AWS Academy: no se pueden crear roles ni leer las políticas del laboratorio

- **Date:** 2026-11-11 · **Source topic:** `planificacion`
- **Finding:** `iam:CreateRole` está denegado y las políticas `Pvoclabs*` no se pueden leer. Existen `LabRole`, `LabInstanceProfile`, `EMR_DefaultRole` y `EMR_EC2_DefaultRole`; todo el pipeline usa esos (convención "Roles de AWS Academy"). Los permisos se descubren probando: `--dry-run` en EC2, parámetros inválidos en RDS/EMR.
- **Provenance:** sesión 2026-11-11 con el rol `voclabs` por CLI.

## [hecho] AWS Academy: Session Manager funciona en las EC2 con `LabInstanceProfile`

- **Date:** 2026-11-11 · **Source topic:** `punto2-fuentes`
- **Finding:** una EC2 con Amazon Linux 2023 y `LabInstanceProfile` aparece `Online` en SSM a los pocos minutos. Con `ssm send-command` (`AWS-RunShellScript`) se corren comandos en la instancia desde el portátil, sin SSH ni `labsuser.pem`; sirve para siembras, verificaciones y automatizar pasos en la EC2. El rol también puede leer y escribir el bucket del proyecto.
- **Provenance:** verificación de `tlc-fuente-archivos` por SSM, sesión 2026-11-11.

## [hecho] EC2 Amazon Linux 2023: `python3` es 3.9 y boto3 ya no lo soporta

- **Date:** 2026-11-11 · **Source topic:** `punto2-fuentes`
- **Finding:** el `python3` del sistema en AL2023 es 3.9.25 y boto3 avisa que dejó de soportarlo (desde 2026-04-29). Instalar `python3.11` con `dnf` y crear un venv con él; no instalar paquetes con pip sobre el Python del sistema. Aplica a cualquier código que corra en una EC2 (fuentes, Streamlit del Punto 8).
- **Provenance:** primera corrida de `punto2-fuentes/sembrar.py`, sesión 2026-11-11.

## [hecho] RDS MariaDB 11.8 exige TLS (`require_secure_transport=ON`)

- **Date:** 2026-11-11 · **Source topic:** `punto2-fuentes`
- **Finding:** `tlc-mariadb` rechaza conexiones sin cifrar (`ERROR 3159`). pymysql conecta sin configurar nada, pero el cliente `mariadb` necesita `--ssl`, y cualquier conexión JDBC (por ejemplo, Glue o Spark leyendo la RDS) tendrá que activar SSL.
- **Provenance:** consulta de evidencias desde la EC2 por SSM, sesión 2026-11-11.

## [regla] Capturas de la consola de AWS: enmascarar el ID de cuenta en todos los frames

- **Date:** 2026-11-11 · **Source topic:** `punto2-fuentes`
- **Finding:** el repo y el Docx son públicos y la consola muestra el ID de cuenta en el menú y en los ARN, a veces dentro de iframes `about:blank` y con caracteres invisibles entre los dígitos. Antes de cada captura, reemplazar el ID en todos los frames y verificar que no quede; si queda, no guardar la captura. Revisar la imagen a ojo antes de usarla.
- **Provenance:** primera tanda de capturas del Punto 2: el ARN de la EC2 se filtró hasta aplicar la máscara por frame (sesión 2026-11-11).

## [hecho] AWS Academy: EventBridge → Lambda → SSM funciona con `LabRole`

- **Date:** 2026-11-13 · **Source topic:** `punto3-ingesta`
- **Finding:** con `LabRole` se puede crear una Lambda (Python 3.12, 2048 MB, 900 s), reservarle concurrencia (`put_function_concurrency` = 1), configurar `put_function_event_invoke_config` y programarla con una regla de EventBridge (`put_rule` + `add_permission` + `put_targets`, sin rol para EventBridge). Desde la Lambda, `ssm:SendCommand` y `GetCommandInvocation` contra la EC2 funcionan, igual que `ec2:DescribeInstances`, `ssm:GetParameter` y lectura y escritura en el bucket. Descarga de CloudFront de la TLC a S3 desde la Lambda: ~65–90 MB/s, ~450 MiB en 5–7 s.
- **Provenance:** despliegue y corridas de `punto3-ingesta/desplegar.py` e `ingestar.py`, y una corrida programada a las 16:28 (sesión 2026-11-13, cuenta de Jean).

## [regla] boto3: las subidas a S3 fallan con `S3UploadFailedError`, no con `ClientError`

- **Date:** 2026-11-15 · **Source topic:** `punto3-ingesta`
- **Finding:** `upload_file` y `upload_fileobj` (el transfer manager de boto3) envuelven el error de S3 en `boto3.exceptions.S3UploadFailedError`, que no hereda de `botocore.exceptions.ClientError`. Un `except ClientError` alrededor de una subida no la atrapa y el proceso se cae. Capturar las dos. Lo mismo con las descargas por streaming: una conexión cortada lanza `OSError` o `http.client.HTTPException`, no `urllib.error.URLError`.
- **Provenance:** revisión del código de `punto3-ingesta/lambda_ingesta.py` y `ec2_ingesta.py` (sesión 2026-11-13); las dos capturas ya cubren estos casos.

## [hecho] Academy: `LabRole` alcanza para Glue 5.0 y Step Functions con `glue:startJobRun.sync`

- **Date:** 2026-11-15 · **Source topic:** `punto4-trusted`
- **Finding:** con `LabRole` funcionan `glue:CreateJob` (Glue 5.0, `G.1X` × 2), `StartJobRun` y `GetJobRun`; `states:CreateStateMachine` con `LabRole` como rol; y una ejecución STANDARD con `arn:aws:states:::glue:startJobRun.sync` que espera el job hasta SUCCEEDED. Desde una Lambda con `LabRole`, `states:ListExecutions` y `states:StartExecution` están permitidos, así que la ingesta puede encadenar la preparación. La salida de `.sync` trae en la raíz `Id`, `JobRunState`, `ExecutionTime`, `DPUSeconds`, `NumberOfWorkers` y `GlueVersion`. Un job de 2 líneas en Glue 5.0 tardó 40 s de ejecución y facturó 81 DPU-segundos. Si un `startJobRun` llega justo cuando termina la corrida anterior de un job con `MaxConcurrentRuns` lleno, Glue responde `ConcurrentRunsExceededException` aunque el `get-job-run` anterior ya diga SUCCEEDED; la tarea necesita `Retry` para ese error.
- **Provenance:** prueba de la fase 0 del plan del Punto 4 (recursos `tlc-prueba-permisos`, sesión 2026-11-15, cuenta de Jean).

## [hecho] Academy: correr varios jobs de Glue a la vez desactivó la cuenta

- **Date:** 2026-11-15 · **Source topic:** `punto4-trusted`
- **Finding:** la cuenta de Jean quedó desactivada ("AWS account deactivated at 2026-11-15T17:37:48-08:00", 01:37:48 UTC) unos dos minutos después de lanzar en paralelo tres jobs de Glue 5.0 `G.1X`: `taxi_zones` con 2 workers y yellow 2024-01 y 2025-01 con 4 cada uno, 10 workers en total. Las credenciales pasaron a tener un deny explícito de `voc-cancel-cred`. Hasta ahí solo habían corrido jobs de a uno, con 2 workers, sin problema. El presupuesto no era la causa: iban 8,6 USD de 50. Vocareum, la plataforma del Learner Lab, revisa "Glue Max Workers", "Glue Max Concurrent jobs" y "Glue Worker Types", y si se pasa alguno "the account will be flagged as fraudulent and deactivated" (https://help.vocareum.com/en/articles/8284823-aws-service-limits). No publica valores por defecto. *Sin verificar* cuál de los tres límites se pasó y qué valores tiene este curso. El "G.1X × 10 aceptado" del finding de límites de Academy era la creación del job, no una corrida. Mientras no se conozcan los límites: un job a la vez y pocos workers.
- **Provenance:** fase 1 del plan del Punto 4 (sesión 2026-11-15) y captura del Learner Lab.

## [hecho] Glue deja marcadores `_$folder$` de 0 bytes en trusted

- **Date:** 2026-11-16 · **Source topic:** `punto4-trusted`
- **Finding:** al escribir con `mode("overwrite")` en `s3://.../trusted/{dataset}/year=YYYY/month=MM/`, Glue crea a veces un objeto vacío del directorio padre, por ejemplo `trusted/yellow/year=2024_$folder$`. No afecta los conteos, pero cae dentro de la ruta de la tabla. Al catalogar (crawler o Hive), hay que excluir `**_$folder$` o borrarlos antes.
- **Provenance:** `aws s3 ls --recursive trusted/` antes y después de `--forzar` de yellow 2024-06, 2026-11-16. Aparecen dos, uno de green y uno de yellow.

## [hecho] AWS Academy: "Start Lab" vuelve a encender la EC2 detenida

- **Date:** 2026-11-16 · **Source topic:** `punto4-trusted`
- **Finding:** la EC2 `tlc-fuente-archivos`, detenida el día anterior con `apagar_infra.py`, apareció `running`, con `LaunchTime` 2026-11-16 12:27 (hora local), cerca de cuando Jean inició el lab. La RDS siguió detenida. Que la encienda "Start Lab" es una inferencia, no está verificada en la documentación de Academy. Después de cada "Start Lab" hay que revisar la EC2 y apagarla si no se va a usar, porque cobra.
- **Provenance:** `aws ec2 describe-instances` y `aws rds describe-db-instances` en la cuenta del segundo curso de Jean, 2026-11-16.

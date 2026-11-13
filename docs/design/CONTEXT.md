# Proyecto 2 Big Data TLC — Agent Context

> **Purpose:** Orient any agent working on this project. Read this first, then stop as soon as the task is clear.
> **Last updated:** 2026-11-13

## Skills

Load by task, not all at once. Solo `memoria-equipo` viene en el repo (`.claude/skills/`), para los otros integrantes; las demás son skills locales de Jean y se usan si existen en la máquina.

| Skill | When to load |
|-------|--------------|
| `memoria-proyecto` (Jean) / `memoria-equipo` (resto del equipo) | Al arrancar, al escribir en `docs/design/` y al cerrar cada sesión |
| `orquesta` | Antes de repartir trabajo entre subagentes; consultar `INDEX.md` primero |
| `de-arquitectura-de-datos` | Forma general de la plataforma (zonas, batch, costos) |
| `de-ingesta-y-etl` | Ingesta desde URL, RDS MariaDB y archivos en EC2 hacia S3 |
| `de-data-lakes` | Zonas, rutas, particionado, formatos y evolución de esquema en S3 |
| `de-orquestacion` | Programar y coordinar el pipeline (schedule, backfill, reintentos) |
| `de-principios-de-diseno` | Escribir o revisar código de pipeline (Lambdas, Glue jobs, PySpark) |
| `de-modelado-dimensional` | Modelar las tablas analíticas que responden las preguntas |
| `handoff` | Al cerrar una sesión o fase y pasar a otra |

## Repositories

| Repo | Purpose | Key paths |
|------|---------|-----------|
| `JeanArdila711/proyecto2-sd` (público) | Este proyecto: código, evidencias y memoria | `docs/design/` |
| `JeanArdila711/fundamentals-dataengineering` | Pipeline TLC del curso; **solo referencia**, no se reutiliza tal cual | `m2-tlc-ingestion/`, `m3-airflow-orchestration/dags/`, `m4-landing-to-raw/`, `m4-raw-to-structured/` |

## Active Context

**Load order:** this file → `{topic}/context.md` of the active topic → the files its document map marks `always` → only the files the task names. Never load `CHANGELOG.md`, `evidence/`, `archive/`, or a whole folder unless the task names the file.
**Active topics:** `planificacion` (preguntas, fuentes y arquitectura de la ingesta cerradas; faltan P2/P3 y el reparto en topics) · `punto2-fuentes` (fuentes funcionando y documentadas en el Docx) · `punto3-ingesta` (ingesta funcionando en AWS y Punto 3 del Docx con evidencias; listo para cerrar con el visto bueno de Jean).
**Known findings:** `findings.md` — 12 entries, last 2026-11-13. Open it only when the task touches a subject it covers.

**Current state (2026-11-13):** Memoria en GitHub (`main`). Decididos el alcance de datos, las 6 preguntas, el reparto de fuentes, la arquitectura de la ingesta y el layout de raw (Conventions). El Docx del enunciado (`SI3007-262-proyecto2.docx`, raíz del repo) tiene llenos integrantes, link del repo, Punto 1 y Punto 2. El Punto 2 funciona en **dos cuentas de Academy** (David y Jean), cada una con su bucket, RDS y EC2, David con 2024-01 a 2024-03 liberados y Jean con 2024-01 a 2025-11. El Punto 3 corre en la cuenta de Jean (`punto3-ingesta/`): EventBridge cada 5 min → Lambda `tlc-ingesta` → `raw/`, con los 23 meses de yellow, green y HVFHV más `taxi_zones` (11,8 GiB), probado también en corrida automática. 2025-12 queda para la demo (Conventions). Todavía no se decide en qué cuenta corre la demo final. Entrega y sustentación presencial: **2026-11-19**.

**Next up:** revisar en Word el Punto 3 del Docx y cerrar el topic `punto3-ingesta`; cerrar las definiciones de P2 y P3; Punto 4 (raw → trusted con Glue y Spark) y partir los Puntos 4–8 en topics.
**Known issues:** en la cuenta de Jean, la EC2 y la RDS están detenidas y la regla de EventBridge deshabilitada desde el cierre del 2026-11-13. Para retomar: `crear_infra.py` y `desplegar.py`. Sin pausarla, la regla sigue disparando con la infraestructura apagada (la parte de la EC2 se omite): `punto3-ingesta/desplegar.py --pausar` al terminar. Las credenciales de Academy expiran con cada sesión del laboratorio. La EC2 y la RDS cobran mientras estén encendidas: `punto2-fuentes/infra/apagar_infra.py` al terminar.

## Conventions

- **Alcance de datos (in force 2026-11-10; owner Jean; source planificacion):** yellow + green + High Volume FHV + Taxi Zone Lookup, 2024 y 2025 completos (72 archivos, 12,38 GiB). FHV tradicional queda fuera. Detalle: `planificacion/current/preguntas-de-negocio.md` § Datos.
- **Solo datos TLC (in force 2026-11-10; owner Jean; source planificacion):** toda pregunta de negocio se responde con datos publicados por la TLC (archivos de viajes y Taxi Zone Lookup). Nada de fuentes externas.
- **Zonas de cobro por congestión (in force 2026-11-10; owner Jean; source planificacion):** las zonas dentro del área de cobro se derivan de los datos de 2025: zonas de destino con `cbd_congestion_fee > 0`. No se usa la definición de la MTA.
- **Pipeline nuevo (in force 2026-11-10; owner Jean; source planificacion):** el pipeline se diseña de cero para este proyecto. `fundamentals-dataengineering` es referencia de patrones, no base de código.
- **Cuenta AWS Academy (in force 2026-11-10; owner Jean; source planificacion):** todo se despliega en AWS Academy, no en la cuenta personal. La migración se planifica después.
- **Fuentes de datos (in force 2026-11-11; owner David; source planificacion):** RDS MariaDB guarda `taxi_zones` y los viajes de green; la EC2 guarda los Parquet de yellow como archivos; HVFHV se ingiere directo de la URL de la TLC. Un simulador libera un mes a la vez en las tres fuentes para demostrar la ingesta automática. Contrato con la ingesta: HVFHV se descarga solo hasta el reloj simulado `/proyecto2-sd/simulacion/mes_actual` (Parameter Store); `green_trips` trae `trip_id` autoincremental y `mes_archivo` para extracción incremental; los archivos de yellow aparecen completos en `/data/tlc/yellow` (escritura atómica). Detalle: `planificacion/current/fuentes-de-datos.md` y `punto2-fuentes/README.md`.
- **Ingesta automática (in force 2026-11-13; owner Jean; source planificacion):** sin Airflow. HVFHV lo ingiere una Lambda (descarga por streaming de la URL de la TLC a S3); yellow y green, un script en la EC2 que lee `/data/tlc/yellow` y MariaDB, ejecutado por SSM Run Command. Una regla programada de EventBridge dispara las dos. Cada corrida compara con lo que ya está en S3 y solo trae los meses que faltan; reingerir un mes reemplaza su partición. Glue JDBC queda descartado para el Punto 3. Encadenar con los Puntos 4 y 5: Step Functions, cuando se llegue ahí.
- **Layout de la zona raw (in force 2026-11-13; owner Jean; source planificacion):** `s3://<bucket>/raw/{yellow,green,hvfhv}/year=YYYY/month=MM/<archivo TLC>.parquet`, un archivo por mes con el nombre de la TLC (`green_tripdata_YYYY-MM.parquet` para lo extraído de MariaDB). `raw/taxi_zones/taxi_zones.parquet` sin partición. Todo en Parquet; la ingesta solo escribe en `raw/`.
- **2025-12 reservado para la demo (in force 2026-11-13; owner Jean; source punto3-ingesta):** en la cuenta de la demo se liberan e ingieren 2024-01 a 2025-11. 2025-12 se libera en vivo en la sustentación (`simular.py --mes 2025-12`) para mostrar la ingesta automática. Los Puntos 4–8 se construyen con 23 meses y tienen que tolerar que el último mes llegue después.
- **Roles de AWS Academy (in force 2026-11-11; owner David; source planificacion):** no se pueden crear roles IAM. Lambdas, Glue y Step Functions usan `LabRole`; la EC2 usa `LabInstanceProfile`; EMR usa `EMR_DefaultRole` / `EMR_EC2_DefaultRole`. Región `us-east-1`. Límites de tamaño en `findings.md`.
- **Infraestructura por scripts (in force 2026-11-11; owner David; source punto2-fuentes):** los recursos de AWS se crean con scripts boto3 idempotentes dentro del directorio de cada punto. Nombres de recursos en `comun/config.py` (`RECURSOS`), etiqueta `Project=proyecto2-sd` en todo, y cada script encuentra lo que creó el anterior por nombre o etiqueta, sin archivos de estado. Contraseñas solo en `config.env` (gitignored); plantilla en `config.example.env`.
- **Repo por punto de la rúbrica (in force 2026-11-10; owner Jean; source planificacion):** el repo tiene un directorio por cada uno de los 8 puntos, con evidencias, código e instrucciones para reproducirlo todo. Lo exige la rúbrica: `planificacion/current/rubrica.md`.
- **Sin secretos en el repo (in force 2026-11-10; owner Jean; source planificacion):** el repo es público. Nada de credenciales, IDs de cuenta ni `.env` en commits.
- **Memoria en el repo, Obsidian para entender (in force 2026-11-10; owner Jean; source planificacion):** `docs/design/` es la fuente de verdad para agentes. Obsidian (`03 - Universidad/Semestre 8/Tópicos Especiales en Telemática/Proyecto 2/`) son las notas del equipo para entender cómo funciona el proyecto (explicaciones, conceptos, preparación de la sustentación). Ningún agente toma decisiones a partir de Obsidian.
- **planificacion-scoped rulings** live in `planificacion/context.md` § Rulings.

# Proyecto 2 Big Data TLC — Agent Context

> **Purpose:** Orient any agent working on this project. Read this first, then stop as soon as the task is clear.
> **Last updated:** 2026-11-10

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
**Active topics:** `planificacion` (preguntas cerradas; faltan fuentes, arquitectura y reparto de trabajo).
**Known findings:** `findings.md` — 5 entries, last 2026-11-10. Open it only when the task touches a subject it covers.

**Current state (2026-11-10):** Repo `main` sin commits: la memoria, `CLAUDE.md`, `AGENTS.md` y `.claude/skills/memoria-equipo/` existen solo en local y no se suben a GitHub hasta que Jean lo diga. Planificación en curso: rúbrica resumida, alcance de datos decidido y las 6 preguntas de negocio escogidas y verificadas contra los parquets. Todavía no hay código ni recursos en AWS. Entrega y sustentación presencial: **2026-11-19**.

**Next up:** definir qué va en RDS MariaDB y qué en EC2 (punto 2 de la rúbrica); cerrar las definiciones de P2 y P3; diseñar la arquitectura nueva; partir el trabajo en topics para agentes.
**Known issues:** las restricciones de AWS Academy (IAM, servicios, sesiones) no están revisadas.

## Conventions

- **Alcance de datos (in force 2026-11-10; owner Jean; source planificacion):** yellow + green + High Volume FHV + Taxi Zone Lookup, 2024 y 2025 completos (72 archivos, 12,38 GiB). FHV tradicional queda fuera. Detalle: `planificacion/current/preguntas-de-negocio.md` § Datos.
- **Solo datos TLC (in force 2026-11-10; owner Jean; source planificacion):** toda pregunta de negocio se responde con datos publicados por la TLC (archivos de viajes y Taxi Zone Lookup). Nada de fuentes externas.
- **Zonas de cobro por congestión (in force 2026-11-10; owner Jean; source planificacion):** las zonas dentro del área de cobro se derivan de los datos de 2025: zonas de destino con `cbd_congestion_fee > 0`. No se usa la definición de la MTA.
- **Pipeline nuevo (in force 2026-11-10; owner Jean; source planificacion):** el pipeline se diseña de cero para este proyecto. `fundamentals-dataengineering` es referencia de patrones, no base de código.
- **Cuenta AWS Academy (in force 2026-11-10; owner Jean; source planificacion):** todo se despliega en AWS Academy, no en la cuenta personal. La migración se planifica después.
- **Repo por punto de la rúbrica (in force 2026-11-10; owner Jean; source planificacion):** el repo tiene un directorio por cada uno de los 8 puntos, con evidencias, código e instrucciones para reproducirlo todo. Lo exige la rúbrica: `planificacion/current/rubrica.md`.
- **Sin secretos en el repo (in force 2026-11-10; owner Jean; source planificacion):** el repo es público. Nada de credenciales, IDs de cuenta ni `.env` en commits.
- **Memoria en el repo, Obsidian para entender (in force 2026-11-10; owner Jean; source planificacion):** `docs/design/` es la fuente de verdad para agentes. Obsidian (`03 - Universidad/Semestre 8/Tópicos Especiales en Telemática/Proyecto 2/`) son las notas del equipo para entender cómo funciona el proyecto (explicaciones, conceptos, preparación de la sustentación). Ningún agente toma decisiones a partir de Obsidian.
- **planificacion-scoped rulings** live in `planificacion/context.md` § Rulings.

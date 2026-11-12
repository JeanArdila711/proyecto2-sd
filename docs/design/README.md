# Proyecto 2 Big Data TLC

**Owner:** Jean Ardila (equipo de SI3007)
**Tracker:** none
**Status:** Planificación en curso; entrega y sustentación el 2026-11-19

## Summary

Caso de estudio de Big Data sobre los registros de viajes de la NYC Taxi & Limousine Commission (TLC), 2024–2025: taxis amarillos, verdes y apps de alto volumen (Uber, Lyft). Responde seis preguntas de negocio sobre competencia entre taxis y apps, economía del conductor, tiempos de espera, propinas y el efecto del cobro por congestión de 2025. Se construye como un pipeline en AWS Academy: fuentes en RDS MariaDB, EC2 y URL, datalake en S3, Glue/Spark, EMR/Hive, Athena y una app en Streamlit.

## Phases

Una fase por punto de la rúbrica (`planificacion/current/rubrica.md`).

| Phase | Outcome | Status |
|-------|---------|--------|
| **1** — Caso de estudio y preguntas | Seis preguntas verificadas contra los datos; escrito en el Docx | In progress (`planificacion`) |
| **2** — Fuentes de datos | RDS = zonas + green, EC2 = yellow, URL = HVFHV; reparto decidido, falta construir | In progress (`planificacion`) |
| **3** — Ingesta automática a S3 | Datos en las zonas del datalake sin pasos manuales | Planned - no topic |
| **4** — Preparación raw → trusted | Glue + Spark | Planned - no topic |
| **5** — Catalogación | Glue Data Catalog + EMR/Hive | Planned - no topic |
| **6** — Analítica SQL | Athena, Hive y SparkSQL respondiendo P1–P6 | Planned - no topic |
| **7** — Analítica PySpark | PySpark respondiendo P1–P6 | Planned - no topic |
| **8** — Visualización y app | Gráficas + Streamlit detrás de API Gateway | Planned - no topic |

## Topics

| Topic | Title | Status |
|-------|-------|--------|
| [`planificacion`](planificacion/context.md) | Planificación del proyecto | In progress |

## Documents

| Topic | Document | Path |
|-------|----------|------|
| — | Agent context | [CONTEXT.md](CONTEXT.md) |
| — | Changelog | [CHANGELOG.md](CHANGELOG.md) |
| — | Findings | [findings.md](findings.md) |
| — | Índice de informes | [INDEX.md](INDEX.md) |
| planificacion | Rúbrica | [rubrica.md](planificacion/current/rubrica.md) |
| planificacion | Preguntas de negocio y datos | [preguntas-de-negocio.md](planificacion/current/preguntas-de-negocio.md) |
| planificacion | Fuentes de datos (Punto 2) | [fuentes-de-datos.md](planificacion/current/fuentes-de-datos.md) |
| — | Documento de entrega (Docx del enunciado) | [SI3007-262-proyecto2.docx](../../SI3007-262-proyecto2.docx) |

## Open decisions

| Decision | Options | Status |
|----------|---------|--------|
| Qué datos van en RDS MariaDB y cuáles en archivos en EC2 | RDS = zonas + green, EC2 = yellow, URL = HVFHV (convención "Fuentes de datos") | Accepted |
| Extracción RDS → S3 | Glue JDBC (requiere red de VPC) / script con cron en la EC2 | Proposed |
| P2: qué tarifa se compara entre yellow y HVFHV | `fare_amount` vs `base_passenger_fare` / con recargos | Proposed |
| P3: denominador del porcentaje que recibe el conductor | Tarifa base / todo lo que paga el pasajero | Proposed |
| Orquestación del pipeline | Airflow / servicios nativos de AWS / otra | Proposed |
| Streamlit detrás de API Gateway | Proxy directo a Streamlit / API Gateway → Lambda → Athena consumida por Streamlit | Proposed |
| Restricciones de AWS Academy | Verificadas por CLI (findings; convención "Roles de AWS Academy") | Accepted |

_States: **Proposed** (options listed, nothing chosen) · **Accepted** (chosen; the rationale goes in the CHANGELOG) · **Deprecated** (no longer relevant) · **Superseded** (replaced; link the new row)._

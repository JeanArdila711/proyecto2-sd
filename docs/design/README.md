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
| **2** — Fuentes de datos | RDS = zonas + green, EC2 = yellow, URL = HVFHV; infraestructura, siembra y simulador funcionando; Punto 2 del Docx con evidencias | In progress (`punto2-fuentes`) |
| **3** — Ingesta automática a S3 | EventBridge → Lambda (HVFHV) + SSM a la EC2 (yellow, green, zonas) → `raw/`; corre sola, idempotente y probada en AWS. Punto 3 del Docx con evidencias | Done (`punto3-ingesta`) |
| **4** — Preparación raw → trusted | Glue + Spark | In progress (`punto4-trusted`) |
| **5** — Catalogación | Base `tlc_trusted` en el Glue Data Catalog (5 tablas, 144 particiones), Athena = controles, Hive en EMR sobre el mismo catálogo y paso `Catalogar` en la state machine | In progress (`punto5-catalogo`): faltan las capturas |
| **6** — Analítica SQL | Athena, Hive y SparkSQL respondiendo P1–P6 | In progress (`puntos6-8-analitica`) |
| **7** — Analítica PySpark | PySpark respondiendo P1–P6 | In progress (`puntos6-8-analitica`) |
| **8** — Visualización y app | Gráficas + Streamlit detrás de API Gateway | In progress (`puntos6-8-analitica`) |

## Topics

| Topic | Title | Status |
|-------|-------|--------|
| [`planificacion`](planificacion/context.md) | Planificación del proyecto | In progress |
| [`punto2-fuentes`](punto2-fuentes/context.md) | Fuentes de datos: infraestructura, siembra y simulador | In progress |
| [`punto3-ingesta`](punto3-ingesta/context.md) | Ingesta automática a la zona raw | Done |
| [`punto4-trusted`](punto4-trusted/context.md) | Preparación raw → trusted con Glue y Spark | In progress |
| [`punto5-catalogo`](punto5-catalogo/context.md) | Catalogación en Glue Data Catalog y EMR/Hive | In progress |
| [`puntos6-8-analitica`](puntos6-8-analitica/context.md) | Analítica SQL y PySpark, visualización y app (compañero, en su cuenta) | In progress |

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
| puntos6-8-analitica | Encargo del compañero: muestra, Puntos 6–8 y entrega por PR | [encargo.md](puntos6-8-analitica/current/encargo.md) |
| punto5-catalogo | README del Punto 5 (qué se creó, por qué, reproducir, resultados) | [README.md](../../punto5-catalogo/README.md) |
| — | Documento de entrega (Docx del enunciado) | [SI3007-262-proyecto2.docx](../../SI3007-262-proyecto2.docx) |

## Open decisions

| Decision | Options | Status |
|----------|---------|--------|
| Qué datos van en RDS MariaDB y cuáles en archivos en EC2 | RDS = zonas + green, EC2 = yellow, URL = HVFHV (convención "Fuentes de datos") | Accepted |
| Extracción RDS → S3 | Script en la EC2 por SSM (convención "Ingesta automática"); Glue JDBC descartado | Accepted |
| Layout de la zona raw | `raw/{dataset}/year=/month=/` (convención "Layout de la zona raw") | Accepted |
| P2: qué tarifa se compara entre yellow y HVFHV | Tarifa base + recargos por milla, razón de sumas (convención "Métrica de P2") | Accepted |
| P3: denominador del porcentaje que recibe el conductor | (`driver_pay` + propina) / todo lo que paga el pasajero (convención "Métrica de P3") | Accepted |
| Orquestación del pipeline | Sin Airflow: EventBridge para la ingesta (convención "Ingesta automática"); Step Functions para encadenar los Puntos 4–5, por confirmar | Accepted |
| Streamlit detrás de API Gateway | Proxy directo a Streamlit / API Gateway → Lambda → Athena consumida por Streamlit; la propone el compañero (`puntos6-8-analitica`), la decide Jean | Proposed |
| Cuenta de la demo final | Jean (convención "Cuenta de la demo") | Accepted |
| Restricciones de AWS Academy | Verificadas por CLI (findings; convención "Roles de AWS Academy") | Accepted |

_States: **Proposed** (options listed, nothing chosen) · **Accepted** (chosen; the rationale goes in the CHANGELOG) · **Deprecated** (no longer relevant) · **Superseded** (replaced; link the new row)._

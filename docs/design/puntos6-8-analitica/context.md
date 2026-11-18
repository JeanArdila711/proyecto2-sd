# puntos6-8-analitica — Context

**Tracker:** none
**Status:** In progress · **Owner:** Andres Felipe Prieto

## Orientation

Puntos 6, 7 y 8 de la rúbrica: analítica SQL (Athena, EMR/Hive y SparkSQL), analítica con PySpark y visualización con Streamlit detrás de API Gateway, respondiendo P1–P6 sobre la base `tlc_trusted`. El compañero los desarrolla en su propia cuenta de Academy sobre una muestra de 3 meses (2024-01 a 2024-03) que arma con los Puntos 2–5, y le manda cada punto a Jean por Pull Request; Jean los corre al final en la cuenta de la demo (convención "Cuenta de la demo"). El encargo completo, con el orden, las reglas, la verificación y la entrega, está en `current/encargo.md`. El topic se cierra cuando los tres PR están integrados, corren en la cuenta de Jean y cada punto tiene su README con evidencias.

## Rulings

- **Un `.sql` por pregunta para los tres motores (Andres Felipe Prieto, 2026-11-17 22:30):** P1–P6 viven una sola vez en `punto6-analitica-sql/consultas/`; `consultas.py` solo reemplaza `{TEXTO}` (`VARCHAR` en Athena, `STRING` en Hive y Spark) y quita los comentarios. SQL común: `CAST(... AS DOUBLE)` en las divisiones, subconsultas en vez de `WITH` y promedios en vez de percentiles (los aproximados difieren entre motores).
- **Hive y SparkSQL en un solo EMR de un nodo (Andres Felipe Prieto, 2026-11-17 22:30):** dos steps en un cluster `m5.xlarge` que se apaga solo, con el patrón de `punto5-catalogo/emr_hive.py`; Spark lee el Glue Data Catalog por `spark-hive-site`. Se descartó SparkSQL en Glue para no correr otro job de Glue.
- **Resultados en `resultados/` (Andres Felipe Prieto, 2026-11-17 22:30):** `s3://<bucket>/resultados/punto6/{athena,hive,sparksql}/{pN}/` y `resultados/punto7/pyspark/{pN}/`, fuera de `raw/` y `trusted/` (`RECURSOS["resultados_prefijo"]`). El Punto 8 lee de ahí.
- **P4 sin esperas de más de 1 hora (Andres Felipe Prieto, 2026-11-17 22:30):** la consulta deja fuera `espera_seg > 3600`, que corresponden a viajes reservados con anticipación y no a la espera de quien pide un carro. Jean puede cambiar el umbral en `p4_espera.sql` (y en `punto7-analitica-pyspark/preguntas.py`).

## Journal (newest first)

**2026-11-17 (Andres Felipe Prieto):** Fase A hecha en la cuenta de Andres: Puntos 2–5 con los scripts tal cual, 2024-01 a 2024-03; `preparar_local.py --estado` con 0 pendientes y 10 controles (raw = detalle = viajes; 70,0 M viajes) y `verificar.py` en OK; 10 jobs de Glue de a uno en 36 min. Fase B: Punto 6 escrito y verificado en la muestra: Athena, Hive y SparkSQL (un EMR de un nodo, 805 s) dan los mismos números en P1–P6 (`comparar.py` OK; P6 vacía sin 2025, como se esperaba). Fase C en curso (`punto7-analitica-pyspark/`). Fase D: propuesta del Punto 8 para Jean en `working/propuesta-punto8.md` (API Gateway no hace de proxy al WebSocket de Streamlit; propone API Gateway → Lambda con los resultados y Streamlit como cliente). Para Jean: la convención "Zonas de cobro por congestión" toma toda zona de destino con **algún** viaje de 2025 con `cbd_fee > 0`; el cobro se aplica al entrar al área, no al destino, así que podría incluir zonas fuera del área. Conviene revisar cuántas zonas salen con los 24 meses. Siguiente: verificar el Punto 7 y abrir los PR.

**2026-11-16 (Jean):** Topic abierto para el compañero de los Puntos 6–8 con el encargo en `current/encargo.md`: muestra de 3 meses en su cuenta (fase A), Punto 6 (fase B), Punto 7 (fase C) y Punto 8 (fase D), con entrega por PR. Siguiente: el compañero arranca por la fase A.

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| `current/encargo.md` | reference | always | Qué hacer y en qué orden: muestra en la cuenta del compañero, Puntos 6–8, reglas de Glue y EMR, verificación y entrega por PR |
| `working/propuesta-punto8.md` | borrador | on-demand | Propuesta para el Punto 8 con fuentes: API Gateway → Lambda con los resultados y Streamlit como cliente; espera la decisión de Jean |

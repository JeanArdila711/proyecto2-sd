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

- **Corridas limpias y con tope (Jean, 2026-11-17 23:50):** `athena.py` y los dos `emr.py` vacían su prefijo de `resultados/` antes de correr (`emr_hive.vaciar`, que rechaza prefijos de menos de tres niveles), y los `emr.py` terminan el cluster si pasa `--tope-min` (180 en el Punto 6, 120 en el 7, 60 en el `emr_hive.py` del Punto 5). `comparar.py` falla si una pregunta está vacía en unos motores y no en otros; si está vacía en todos, avisa. Base y rutas salen de `RECURSOS` y llegan a los scripts de EMR por argumentos.

- **Punto 8: Streamlit como cliente de API Gateway (Jean, 2026-11-18 00:00):** API Gateway (HTTP API `tlc-resultados`) → Lambda `tlc-resultados` que sirve `resultados/punto6/athena/pN/resultado.csv` como JSON; Streamlit en una EC2 aparte (`tlc-streamlit`, t3.small) consume esa API, con el 8501 abierto solo a la IP de quien presenta. Las gráficas estáticas salen de la misma API con matplotlib. Streamlit detrás de API Gateway se descartó por la prueba en Academy (WebSocket 400). Detalle: `punto8-visualizacion-app/README.md` y `working/propuesta-punto8.md`. Lo construyó Jean por la fecha de entrega.

## Journal (newest first)

**2026-11-18 17:10 (Jean, con Claude):** Jean pidió el Docx en unas 20 páginas o menos. Los Puntos 4–8 se rehicieron en versión corta (~8 páginas, unas 1.600 palabras): 10 figuras (13 a 22) con las capturas recortadas, sin la barra de la cuenta, y las seis gráficas en una sola figura de 2×3. Las respuestas a P1–P6 van en una tabla del Punto 8 y queda un extracto de código en los Puntos 6 y 7. El detalle completo sigue en los README de cada punto. Los Puntos 1–3 quedaron igual (~12 páginas). `validate.py` pasa.

**2026-11-18 16:40 (Jean, con Claude):** Docx con los Puntos 4 a 8 llenos, con el mismo formato de los Puntos 1–3: arquitectura, decisiones, resultados, cómo reproducir, figuras 13 a 38 (capturas y las seis gráficas) y extractos de código. En el Punto 8 van las respuestas a P1–P6, verificadas contra la API: el handoff decía que la propina de P5 variaba entre 21 % y 24 % según la hora, pero va de 17,9 % (5 a. m.) a 23,7 %. `validate.py` pasa; no se pudo renderizar porque Word no respondió por AppleScript. Siguiente: Jean lo revisa en Word.

**2026-11-18 15:50 (Jean, con Claude):** Capturas de los Puntos 6, 7 y 8 en sus `evidencias/` y enlazadas en los README: Athena con P1 (537 filas), los dos EMR `tlc-analitica` con sus steps `Completed`, `comparar.py --con-pyspark` de nuevo OK en P1–P6, la API `tlc-resultados` con sus dos rutas integradas con la Lambda, `GET /resultados/p6` y tres pestañas del tablero (P1, P2, P6). Para esto se corrió `desplegar.py` (prueba en la EC2 OK) y después `--apagar`. Al cierre: las dos EC2 detenidas, 0 EMR activos. Siguiente: llenar el Docx y avisarle a Andres.

**2026-11-18 01:00 (Jean):** Recálculo con el tope de 100 millas terminado: EMR del Punto 6 en 47 min (Hive 32, SparkSQL 10) y del Punto 7 en 15 min, todos los steps `COMPLETED`; `comparar.py --con-pyspark` OK en P1–P6 en los cuatro motores. Tablas finales en los README de los Puntos 6 y 7. Nada encendido en AWS al cierre. Siguiente: capturas (README § Evidencias de los Puntos 4–8) y el Docx; antes de la sustentación, `punto8-visualizacion-app/desplegar.py` desde la red de la sala.

**2026-11-18 00:15 (Jean):** Punto 8 construido y desplegado en la cuenta de la demo (ruling "Punto 8: Streamlit como cliente de API Gateway"): API `tlc-resultados` con `GET /resultados` y `/resultados/{pregunta}`, Streamlit en `tlc-streamlit` con una pestaña por pregunta, `test_app.py` (AppTest) en verde en la EC2 y seis PNG en `punto8-visualizacion-app/graficas/`. Revisión del `revisor` sin bloqueantes; arreglados el permiso de la Lambda (se reemplaza siempre), las IPs viejas del 8501 (se revocan), los timeouts de SSM y el borrado del security group. Al graficar P2 apareció que yellow tiene viajes de miles de millas que suman el 41 % de sus millas (`findings.md`): P2 y P5 llevan ahora `<= 100` millas y el taxi amarillo pasa de ser el más barato por milla (4,30 USD) al más caro (7,31). Athena ya está recalculado (la app y las gráficas leen de ahí). Las zonas de Brooklyn con propina en 0 se presentan con advertencia (`findings.md`). Quedó corriendo la cadena EMR del Punto 6 → Punto 7 → `comparar.py --con-pyspark` con el corte. Siguiente: correr `comparar.py --con-pyspark` y, si da OK, poner la tabla final en los README de los Puntos 6 y 7.

**2026-11-17 23:50 (Jean):** Revisión de los PR #1 y #2 (ya en `main`) con el `revisor`: sin bloqueantes en P1–P5. P6 medida en la cuenta de la demo con 2025 completo: la regla vieja daba 261 zonas de cobro, así que se cambió la convención "Zonas de cobro por congestión" (38 zonas, todas de Manhattan) y el umbral se compara con enteros en los cuatro motores. Arreglados también el tope de los EMR, los resultados viejos que podían pasar por buenos, las rutas fijas y los joins de P5 en PySpark (ruling "Corridas limpias y con tope"). Segunda revisión sin bloqueantes. Corrida con los 24 meses: Athena 14,2 GiB; EMR del Punto 6 en 48 min y del Punto 7 en 15 min, todos los steps `COMPLETED`; `comparar.py --con-pyspark` OK en P1–P6 (537, 18.596, 253, 249, 291 y 96 filas). Punto 8: prueba en Academy de una HTTP API con `HTTP_PROXY` a Streamlit: HTTP pasa y el WebSocket da 400 (directo, 101). Queda probado que la propuesta de Andres hace falta. Resultados en `working/propuesta-punto8.md` y `punto8-visualizacion-app/README.md`. Siguiente: Jean aprueba la propuesta del Punto 8 y Andres lo construye; capturas de los Puntos 6 y 7.

- 2026-11-17 (Andres): Punto 7 con DataFrames de PySpark; `comparar.py --con-pyspark` OK en la muestra.
- 2026-11-17 (Andres): muestra de 3 meses en su cuenta (Puntos 2–5) y Punto 6 verificado en la muestra; propuesta del Punto 8 en `working/propuesta-punto8.md`.
- 2026-11-16 (Jean): topic abierto con el encargo en `current/encargo.md`.

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| `current/encargo.md` | reference | always | Qué hacer y en qué orden: muestra en la cuenta del compañero, Puntos 6–8, reglas de Glue y EMR, verificación y entrega por PR |
| `working/propuesta-punto8.md` | borrador | on-demand | Propuesta para el Punto 8 con fuentes y la prueba en Academy (el WebSocket de Streamlit no pasa por API Gateway): API Gateway → Lambda con los resultados y Streamlit como cliente; espera la decisión de Jean |

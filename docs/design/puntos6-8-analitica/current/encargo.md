# Encargo: Puntos 6, 7 y 8 en la cuenta del compañero

Lo escribió Jean el 2026-11-16 para el compañero que hace los Puntos 6–8 y para sus agentes. Dice qué hacer, en qué orden, con qué reglas y cómo entregarlo. Las decisiones del proyecto están en `docs/design/CONTEXT.md` § Conventions; este documento las nombra y no las repite. Si algo de acá choca con CONTEXT, gana CONTEXT y hay que avisarle a Jean.

## Para qué

La demo corre en la cuenta de Jean (convención "Cuenta de la demo"), que tiene los 24 meses (2024-01 a 2025-12) en raw, trusted y el catálogo. Recargar todo en otra cuenta tarda unas 5 h de Glue, así que vos armás una **muestra chica de 3 meses** (2024-01 a 2024-03) en tu cuenta, con el mismo código, y sobre ella desarrollás y probás los Puntos 6, 7 y 8. Cuando esté listo, se lo mandás a Jean (sección "Entrega") y él lo corre una vez en su cuenta sobre los datos completos. Por eso **todo tiene que funcionar en las dos cuentas sin cambiar el código**.

## Lo que ya existe y no se toca

Los Puntos 2 a 5 están hechos y verificados. No se modifica su código; si algo de ahí te estorba, se lo decís a Jean.

| Qué | Dónde se explica |
|---|---|
| Fuentes (RDS, EC2, URL) y simulador | `punto2-fuentes/README.md` |
| Ingesta a `raw/` | `punto3-ingesta/README.md` |
| Preparación `raw/` → `trusted/` (Glue + Step Functions), columnas, banderas | `punto4-preparacion/README.md` y `punto4-preparacion/contrato.py` |
| Catálogo: base `tlc_trusted` con `yellow`, `green`, `hvfhv`, `viajes`, `taxi_zones`; Athena (workgroup `tlc-consultas`); Hive en EMR | `punto5-catalogo/README.md` |

Lo que más vas a usar:
- **Qué tabla responde cada pregunta** (convención "Layout de la zona trusted"): P1, P2 y P6 desde `viajes`; P3, P4 y P5 desde la tabla de su servicio (`hvfhv` o `yellow`), con join a `taxi_zones` cuando hace falta la zona.
- **Las preguntas y sus campos:** `docs/design/planificacion/current/preguntas-de-negocio.md`.
- **Métricas ya cerradas:** convenciones "Métrica de P2" y "Métrica de P3". Son razón de sumas, no promedio de razones.
- **Zonas del cobro por congestión (P6):** convención "Zonas de cobro por congestión": se derivan de los datos de 2025.
- **Particiones como texto:** `WHERE year = '2025' AND month = '01'`, no `year = 2025` (`punto5-catalogo/README.md`).
- **Banderas de calidad:** ninguna fila se borró en trusted. Cada consulta filtra las banderas que le importan (por ejemplo, `NOT duracion_invalida AND NOT distancia_invalida` para P2). Decí en cada consulta cuáles usaste y por qué.

## Reglas duras

- **Glue: un job a la vez, con 2 workers.** Varios jobs a la vez dejaron una cuenta del proyecto inutilizable, y los límites de AWS Academy no se conocen (`findings.md`). No subas `glue_workers` ni `preparacion_concurrencia` en `comun/config.py`.
- **EMR: un solo nodo `m5.xlarge`, que se apague solo al terminar.** Es lo único probado (`findings.md`, "EMR de un nodo con Hive"). Reusá el patrón de `punto5-catalogo/emr_hive.py`: subred elegida por zona, `KeepJobFlowAliveWhenNoSteps=False`, nunca dos clusters a la vez. Si necesitás un cluster vivo para iterar, terminálo apenas acabes.
- **Infraestructura con scripts boto3 idempotentes** dentro del directorio de cada punto, nombres nuevos en `RECURSOS` de `comun/config.py`, etiqueta `Project=proyecto2-sd` (convención "Infraestructura por scripts"). El bucket sale de `config.nombre_bucket()`, nunca escrito a mano.
- **Repo público:** nada de credenciales, IDs de cuenta (12 dígitos) ni `config.env` en commits. Al pegar salidas de AWS o capturas, ocultá el ID de la cuenta y el sufijo del bucket.
- **Memoria del proyecto:** con la skill del repo `memoria-equipo` (`.claude/skills/memoria-equipo/SKILL.md`): arranque, escritura en `docs/design/` y cierre de sesión con `design_check.py` sin FAIL.
- **Apagar al terminar cada sesión:** `python punto2-fuentes/infra/apagar_infra.py`. "Start Lab" vuelve a encender la EC2 (observado tres veces, `findings.md`): revisala al arrancar.

## Fase A: muestra de 3 meses en tu cuenta (~45 min, casi todo espera)

Desde la raíz del repo. Antes, lo del README principal: credenciales de tu Learner Lab en `~/.aws/credentials` como perfil `[academy]`, `.venv` con `requirements.txt`, y `cp config.example.env config.env`.

```bash
git pull
python punto2-fuentes/infra/crear_infra.py           # EC2, RDS y bucket (~10 min por la RDS)
python punto2-fuentes/sembrar.py                     # zonas en MariaDB
python punto2-fuentes/simular.py --desde 2024-01 --hasta 2024-03   # libera SOLO los 3 meses
python punto2-fuentes/simular.py --estado            # confirmar 2024-01..2024-03 en las tres fuentes
python punto4-preparacion/desplegar.py               # Glue job, Lambda de pendientes, state machine
python punto3-ingesta/desplegar.py                   # Lambda de ingesta y regla de EventBridge
python punto3-ingesta/desplegar.py --pausar          # la regla queda apagada; la ingesta va a mano
python punto3-ingesta/ingestar.py                    # raw de los 3 meses; al final dispara la preparación
python punto4-preparacion/preparar_local.py --ejecutar   # repetir hasta que --estado dé 0 pendientes
python punto4-preparacion/preparar_local.py --estado
python punto5-catalogo/desplegar.py                  # base tlc_trusted, tablas y paso Catalogar
python punto5-catalogo/verificar.py                  # Athena = controles
python punto2-fuentes/infra/apagar_infra.py          # la EC2 y la RDS ya no hacen falta
```

- El orden importa: `punto4` se despliega antes que `punto3`, para que la Lambda de ingesta encuentre la state machine, y `punto5` después de que trusted tenga datos.
- La parte de la EC2 (yellow, green y zonas) termina después que la Lambda. Los meses que lleguen tarde los procesa el `--ejecutar` siguiente.
- **Listo cuando** `--estado` muestra 0 pendientes y 10 controles (3 meses × 3 servicios + `taxi_zones`), con `filas_raw == filas_detalle == filas_viajes`, y `verificar.py` termina en "OK". Son unos 10 jobs de Glue de 2–6 min, de a uno.
- **No liberes meses de 2025.** HVFHV bajaría todos los meses intermedios. En la muestra no hay cobro por congestión (`cbd_fee` es NULL en 2024), así que **P6 se escribe y se prueba que corra, pero su resultado real sale en la cuenta de Jean**.

## Fase B: Punto 6, analítica SQL (Athena, Hive y SparkSQL)

Rúbrica: analítica descriptiva con SQL en AWS Athena, EMR/Hive y SparkSQL (`planificacion/current/rubrica.md`).

1. **Una consulta por pregunta (P1–P6)** en `punto6-analitica-sql/`, en archivos `.sql` legibles, con un comentario arriba: qué pregunta responde, qué tabla usa, qué banderas filtra y por qué.
2. **Athena:** las seis, con el workgroup `tlc-consultas` y la base `tlc_trusted`. Un script que las corra y guarde el resultado (CSV o Parquet chico) en el bucket, fuera de `raw/` y `trusted/` (por ejemplo `refined/` o `resultados/`; elegí y documentalo).
3. **Hive en EMR:** las mismas consultas (o las que Hive soporte; anotá las diferencias de dialecto) como steps de un cluster de un nodo que se apaga solo, siguiendo `punto5-catalogo/emr_hive.py`.
4. **SparkSQL:** las mismas consultas con `spark.sql(...)` sobre el Glue Data Catalog, en EMR (step `spark-submit` en el mismo patrón) o en un Glue job (de a uno, 2 workers). Elegí uno y explicá por qué.
5. **Verificación:** en la muestra, los tres motores tienen que dar los mismos números en cada pregunta. Un script que lo compare es mejor que mirarlo a ojo.

## Fase C: Punto 7, analítica con PySpark

Las seis preguntas con la API de DataFrames de PySpark (no `spark.sql`), en `punto7-analitica-pyspark/`, leyendo las tablas del catálogo o los Parquet de `trusted/`. Mismo entorno que elegiste para SparkSQL. Verificación: mismos números que el Punto 6.

## Fase D: Punto 8, visualización y app detrás de API Gateway

Rúbrica: gráficas (matplotlib, Dash, Power BI, Grafana, etc.) y una app en **Streamlit expuesta por API Gateway**.

- **Decisión abierta, la proponés vos y la decide Jean** (README § Open decisions, "Streamlit detrás de API Gateway"). Hay dos caminos: API Gateway como proxy directo a un Streamlit en una EC2, o API Gateway → Lambda que sirve los resultados del Punto 6 y un Streamlit que los consume. *Sin verificar*: Streamlit usa WebSockets, y no está claro que un proxy HTTP de API Gateway los soporte. **Verificalo en la documentación de AWS antes de construir** y mandale a Jean la propuesta con la fuente.
- Las gráficas salen de los resultados guardados del Punto 6, no de consultas en vivo sobre trusted (Athena cobra por dato escaneado).
- Código en `punto8-visualizacion-app/`.

## Entrega: cómo le mandás el trabajo a Jean

- **Una rama por punto** (`punto6-analitica-sql`, `punto7-analitica-pyspark`, `punto8-visualizacion-app`) y un **Pull Request a `main`** por cada una. No hagas push directo a `main`. Jean revisa el PR, lo integra y lo corre en su cuenta.
- Cada punto lleva su `README.md` con la estructura de `punto3-ingesta/README.md`: qué se hizo, por qué así (y qué se descartó), archivos, reproducir, evidencias y resultados de la muestra. Incluí **el comando exacto que Jean tiene que correr en su cuenta**.
- La memoria: al cerrar cada sesión, el journal de `docs/design/puntos6-8-analitica/context.md`, la entrada del CHANGELOG y `design_check.py` sin FAIL (skill `memoria-equipo`). Las decisiones que tomes van a § Rulings de ese `context.md`; si alguna cambia algo de CONTEXT § Conventions, se la consultás a Jean antes.
- **Avisale a Jean cuando abras cada PR**, con un resumen corto: qué hace, qué probaste en la muestra, qué no pudiste probar (por ejemplo, P6 sin 2025) y qué tiene que correr él.
- Fecha: entrega y sustentación el **2026-11-19**. Mandá cada punto apenas esté, no los tres juntos al final.

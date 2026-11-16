# Encargo: muestra de trusted en la cuenta de David y Punto 5 (catalogación)

Escrito por Jean el 2026-11-16 para David y sus agentes. Dice qué hay que hacer, en qué orden y con qué reglas. Las decisiones del proyecto están en `docs/design/CONTEXT.md` § Conventions. Este documento las nombra y no las repite. Si algo de acá choca con CONTEXT, gana CONTEXT y hay que avisarle a Jean.

## Para qué

La demo corre en la cuenta de Jean (convención "Cuenta de la demo"), donde trusted tiene los 72 meses. Recargar todo en otra cuenta tarda unas 4 horas de Glue y arriesga la cuenta, así que David no lo hace. Arma una muestra chica en su cuenta, con el mismo formato, y sobre ella desarrolla y prueba los scripts del Punto 5. Cuando los scripts estén listos, Jean los corre una vez en su cuenta sobre los datos completos. Por eso todo tiene que funcionar en las dos cuentas sin cambiar el código.

## Lo que ya existe y no se toca

- `raw/` (Punto 3) y `trusted/` (Punto 4). El layout está en la convención "Layout de la zona trusted":
  - `trusted/{yellow,green,hvfhv}/year=YYYY/month=MM/`: detalle por servicio, todas las filas, nombres en minúscula y banderas de calidad.
  - `trusted/viajes/servicio=X/year=YYYY/month=MM/`: tabla común a los tres servicios, con zonas y tarifa en componentes.
  - `trusted/taxi_zones/`: sin partición.
  - `trusted/_control/`: un JSON por (dataset, mes) con los conteos. **No es una tabla.** No se cataloga.
- El esquema exacto de cada tabla sale de `punto4-preparacion/contrato.py`: `DETALLE`, `derivadas()` y `banderas()` para el detalle, y `viajes()` para `viajes`. Los tipos reales se leen en `esquema_detalle` de cualquier control.
- `servicio`, `year` y `month` **no son columnas del Parquet**: salen de la ruta y se declaran como particiones. `month` va con cero adelante (`01`). Si la tabla lo declara como entero, la proyección de particiones o el `MSCK` tienen que respetar ese formato.
- Las filas dudosas no se borran. Cada consulta filtra por las banderas que le importan.
- Qué tabla responde cada pregunta: P1, P2 y P6 desde `viajes`; P3, P4 y P5 desde la tabla de su servicio.

## Reglas duras

- **Glue: un job o un crawler a la vez.** Tres jobs a la vez desactivaron la primera cuenta de Jean (`findings.md`). Los límites de Vocareum no se conocen y no se van a conocer. No subas `glue_workers` ni `preparacion_concurrencia` en `comun/config.py`.
- **EMR:** cluster chico, `EMR_DefaultRole` / `EMR_EC2_DefaultRole`, y terminarlo apenas acabe la prueba. Los límites de EMR en Academy tampoco se conocen.
- Infraestructura con scripts boto3 idempotentes en `punto5-catalogo/`, nombres nuevos en `RECURSOS` de `comun/config.py` y etiqueta `Project=proyecto2-sd` (convención "Infraestructura por scripts"). El bucket sale de `config.nombre_bucket()`, nunca escrito a mano.
- Repo público: nada de credenciales, ID de cuenta ni `config.env` en commits. Al pegar salidas de AWS, enmascarar el ID de 12 dígitos.
- La memoria del proyecto se lleva con la skill del repo `memoria-equipo`: arranque, escritura en `docs/design/` y cierre de sesión con `design_check.py`.

## Fase A: muestra en la cuenta de David

Ya están liberados 2024-01 a 2024-03 en las fuentes del Punto 2. Desde la raíz del repo, con `config.env` apuntando a tu perfil de Academy:

```bash
git pull
python punto2-fuentes/infra/crear_infra.py          # enciende la EC2 y la RDS si estaban detenidas
python punto2-fuentes/simular.py --estado           # confirmar 2024-01..2024-03 en las tres fuentes
python punto4-preparacion/desplegar.py              # Glue job, Lambda de pendientes y state machine
python punto3-ingesta/desplegar.py                  # Lambda de ingesta y regla de EventBridge
python punto3-ingesta/desplegar.py --pausar         # la regla queda apagada; la ingesta se dispara a mano
python punto3-ingesta/ingestar.py                   # raw de los 3 meses; al final dispara la preparación
python punto4-preparacion/preparar_local.py --ejecutar   # repetir hasta que --estado dé 0 pendientes
python punto4-preparacion/preparar_local.py --estado
```

- El orden importa: `punto4` se despliega antes que `punto3` para que la Lambda de ingesta encuentre la state machine.
- La parte de la EC2 (yellow, green y zonas) termina después que la Lambda. Por eso los meses que lleguen tarde se procesan con el `--ejecutar` siguiente.
- Listo cuando `--estado` muestra 0 pendientes y 10 controles: 3 meses × 3 servicios más `taxi_zones`. En cada uno, `filas_raw == filas_detalle == filas_viajes`. Son unos 10 jobs de ~2–3 min, de a uno.
- 2024 no tiene `cbd_congestion_fee`. Las consultas del cobro por congestión van a salir vacías en la muestra, y eso es lo esperado: se validan en la cuenta de Jean. No liberes meses de 2025, porque HVFHV bajaría todos los meses intermedios.
- Al terminar cada sesión: `python punto2-fuentes/infra/apagar_infra.py`. Ojo: "Start Lab" parece volver a encender la EC2 (`findings.md`), así que revisala al arrancar.

## Fase B: Punto 5, catalogación

Entregable de la rúbrica: tablas SQL en el Glue Data Catalog y en EMR/Hive (`planificacion/current/rubrica.md`).

1. Una base de datos del catálogo con cinco tablas: `yellow`, `green`, `hvfhv`, `viajes` y `taxi_zones`, con sus particiones.
2. Tablas consultables desde Athena, con un workgroup o una ubicación de resultados dentro del bucket, fuera de `raw/` y `trusted/`.
3. Las mismas tablas visibles desde Hive en un cluster EMR. Una opción es usar el Glue Data Catalog como metastore de Hive, con la clasificación `hive-site` de EMR; *sin verificar*, hay que confirmarlo en la documentación de EMR antes de elegirlo. La otra es DDL propio en Hive.
4. Excluir los objetos `**_$folder$` que deja Glue dentro de las rutas de las tablas (`findings.md`), y no catalogar `trusted/_control/`.

Decisiones que son de David, para registrar como ruling en `punto5-catalogo/context.md` y avisarle a Jean:
- **Crawler o DDL.** El crawler es lo más "Glue" a la vista para la rúbrica, pero infiere tipos y particiones por su cuenta y corre como un recurso más de Glue. El DDL (Athena o `glue.create_table` con el esquema de `contrato.py`) es determinista e idempotente. Cualquiera de las dos sirve si el resultado es el mismo en las dos cuentas.
- **Particiones.** `MSCK REPAIR TABLE`, `batch_create_partition` o partition projection. Con projection no hay que registrar meses nuevos cuando llega uno.

**Verificación:** en Athena, `count(*)` por tabla y por partición tiene que dar lo mismo que `filas_detalle` y `filas_viajes` de los controles de la muestra. La misma cuenta desde Hive en EMR, sobre al menos una tabla. Las capturas para el README van con el ID de cuenta enmascarado.

**Entrega del punto:**
- `punto5-catalogo/README.md` con la estructura de `punto3-ingesta/README.md`: qué se creó, por qué así, cómo reproducir y evidencias.
- Una línea en el README que diga el comando que Jean tiene que correr en su cuenta.

## Después (no es parte de este encargo)

Los Puntos 6 (SQL en Athena, Hive y SparkSQL), 7 (PySpark) y 8 (visualización y Streamlit detrás de API Gateway) siguen el mismo patrón: se desarrollan sobre la muestra y se corren al final en la cuenta de Jean. Cada uno abre su topic con `memoria-equipo`. Antes del 6 tienen que cerrarse las definiciones de P2 y P3, que también son de David (README § Open decisions).

# Punto 5 — Catalogación en el Glue Data Catalog y EMR/Hive

La zona **trusted** del [Punto 4](../punto4-preparacion/) queda registrada como tablas SQL en el **AWS Glue Data Catalog**, en la base `tlc_trusted`. Athena las consulta directo, y Hive en EMR las ve sin DDL propio porque usa el mismo catálogo como metastore. El catálogo se mantiene solo: el último paso de la state machine del Punto 4 registra las particiones de los meses nuevos.

```
Step Functions tlc-preparacion
  Pendientes -> Map (Glue job por mes) -> Fallidos -> Catalogar (Lambda tlc-catalogo) -> Hubo fallas
                                                          │
                       trusted/_control/*.json ──────────>│  tablas y particiones que faltan
                                                          ▼
                                    Glue Data Catalog: base tlc_trusted
                                      ├── Athena (workgroup tlc-consultas, resultados en s3://<bucket>/athena/)
                                      └── Hive en EMR (hive-site -> AWSGlueDataCatalogHiveClientFactory)
```

## Tablas

| Tabla | Ubicación | Particiones | Responde |
|---|---|---|---|
| `yellow`, `green`, `hvfhv` | `trusted/{servicio}/` | `year`, `month` (24 cada una) | P3, P4, P5 |
| `viajes` | `trusted/viajes/` | `servicio`, `year`, `month` (72) | P1, P2, P6 |
| `taxi_zones` | `trusted/taxi_zones/` | — | joins con zonas |

Las particiones son `string`, con el mismo texto de la ruta: `WHERE year = '2025' AND month = '01'`. `servicio`, `year` y `month` no son columnas del Parquet: salen de la ruta. `trusted/_control/` no es una tabla y no se cataloga.

## Por qué así

- **Sin crawler.** Un crawler infiere los tipos de los datos y, con esquemas que cambian entre 2024 y 2025 (`cbd_congestion_fee` aparece en 2025), puede partir una tabla o cambiar tipos sin aviso. Los tipos se toman del `esquema_detalle` que el job de Glue escribe en cada control, que son los tipos reales del Parquet, y los de `viajes` se derivan de `contrato.viajes()`. Si los tres servicios no dan los mismos tipos en `viajes`, el catálogo falla en vez de registrar algo mal.
- **Particiones solo de meses con control.** Un mes sin control está a medio preparar o falló. Así ninguna consulta ve un mes incompleto.
- **Sin partition projection.** La usa Athena, pero no Hive, que necesita las particiones registradas en el metastore.
- **Encadenado.** La Lambda `tlc-catalogo` corre al final de cada ejecución de la state machine, también si algún mes falló, y registra solo lo que falta. Si la Lambda falla, la ejecución termina en `Fallo` con el error en `$.error_catalogo`.
- **EMR de un nodo que se apaga solo.** Los límites de EMR de AWS Academy no se conocen. La prueba de Hive usa un solo `m5.xlarge` (el m5 más chico de EMR 7.x), y el cluster termina al acabar el step.

## Archivos

| Archivo | Qué hace |
|---|---|
| `catalogo.py` | Lee los controles y asegura la base, las 5 tablas y las particiones (`create_table`, `batch_create_partition`). Es la Lambda `tlc-catalogo` y la usa `desplegar.py` |
| `test_catalogo.py` | Tipos de `viajes`, particiones y ubicaciones, sin AWS |
| `desplegar.py` | Workgroup de Athena, Lambda, corrida inicial y paso `Catalogar` en la state machine. `--borrar` lo quita todo menos los datos |
| `verificar.py` | `count(*)` por tabla y partición en Athena contra los controles, y un `SELECT *` por tabla para probar los tipos |
| `emr_hive.py`, `hive.q` | Cluster EMR de un nodo con Hive sobre el Glue Data Catalog; corre `hive.q` y se apaga |

El paso `Catalogar` se agrega en `punto4-preparacion/desplegar.py` solo si la Lambda `tlc-catalogo` existe, así que el Punto 4 se puede desplegar sin el 5.

## Reproducir

Desde la raíz del repo, con trusted ya preparada (Punto 4):

```bash
python punto5-catalogo/test_catalogo.py      # ok
python punto5-catalogo/desplegar.py          # catálogo + paso Catalogar en la state machine
python punto5-catalogo/verificar.py          # Athena contra los controles; exit 1 si algo no cuadra
python punto5-catalogo/emr_hive.py           # muestra el cluster que lanzaría, sin crear nada
python punto5-catalogo/emr_hive.py --lanzar  # Hive en EMR (~13 min), se apaga solo
```

En otra cuenta los mismos comandos funcionan sin cambios: el bucket sale de `config.nombre_bucket()` y los nombres de `RECURSOS` en `comun/config.py`.

## Evidencias

Capturas del 2026-11-18 en la cuenta de la demo. En las de la consola se ocultaron el ID de la cuenta, el usuario y el sufijo del bucket.

| Figura | Qué muestra |
|---|---|
| [Glue Data Catalog](evidencias/punto5-1-glue-catalogo.jpg) | La base `tlc_trusted` con sus 5 tablas Parquet |
| [Athena](evidencias/punto5-2-athena-consulta.jpg) | Viajes por servicio y año desde `tlc_trusted.viajes` en el workgroup `tlc-consultas`; suman lo mismo que los controles |
| [EMR](evidencias/punto5-3-emr-hive.jpg) | El cluster `tlc-hive` terminado solo, con el step `hive.q` `Completed` |

## Resultados (2026-11-16)

Despliegue en la cuenta de la demo:

```
workgroup de Athena tlc-consultas: creado
Lambda tlc-catalogo: creada
base tlc_trusted: creada
    green       tabla creada      particiones  24 (24 nuevas)
    hvfhv       tabla creada      particiones  24 (24 nuevas)
    taxi_zones  tabla creada      particiones   0 (0 nuevas)
    viajes      tabla creada      particiones  72 (72 nuevas)
    yellow      tabla creada      particiones  24 (24 nuevas)
paso Catalogar (Punto 5): incluido
```

Una segunda corrida de la Lambda no creó ninguna partición.

`verificar.py`, Athena contra los controles (37 s, 125 MiB escaneados):

```
tabla       particiones   filas Athena  filas control
yellow               24     89,892,322     89,892,322
green                24      1,251,593      1,251,593
hvfhv                24    483,060,132    483,060,132
viajes               72    574,204,047    574,204,047
taxi_zones            1            265            265
OK: Athena coincide con los controles
```

`cbd_fee` en `viajes` es NULL en todo 2024 y tiene valores en todo 2025 de yellow y HVFHV (en green, 587.551 de 591.375 viajes de 2025).

Hive en EMR (`emr-7.14.0`, un `m5.xlarge`): el cluster terminó solo en 778 s con el step `COMPLETED`. Hive listó las 5 tablas y las 24 particiones de green desde el Glue Data Catalog, y contó:

| Consulta | Hive | Controles |
|---|---|---|
| `taxi_zones` | 265 | 265 |
| `green`, suma de los 24 meses | 1.251.593 | 1.251.593 |
| `viajes` con `servicio = 'green'` | 1.251.593 | 1.251.593 |
| `yellow` 2025-01 | 3.475.226 | 3.475.226 |

Un primer intento falló a los 31 s sin crear nada: la subred elegida estaba en una zona de us-east-1 sin `m5.xlarge`. `emr_hive.py` ahora elige una subred en una zona que ofrezca ese tipo.

# Punto 4 — Preparación raw → trusted con Glue y Spark

Un **Glue job en Spark** (`tlc-preparacion`, Glue 5.0) toma un mes de un dataset de la zona **raw** del [Punto 3](../punto3-ingesta/) y lo deja validado, tipado y con banderas de calidad en la zona **trusted**. Una **state machine de Step Functions** calcula qué meses faltan y corre un job por mes. La Lambda de ingesta la dispara al terminar, así que un mes nuevo llega de la fuente a trusted sin que nadie haga nada. Al final, el paso `Catalogar` del [Punto 5](../punto5-catalogo/) lo registra en el Glue Data Catalog.

```
Lambda tlc-ingesta ──StartExecution──> Step Functions tlc-preparacion
                                         Pendientes (Lambda tlc-preparacion-pendientes)
                                           └─> Map, de a 1 ──> Glue job tlc-preparacion (un dataset-mes)
                                                                  raw/{dataset}/year=/month=/*.parquet
                                                                    ├─> trusted/{dataset}/year=/month=/          detalle
                                                                    ├─> trusted/viajes/servicio=/year=/month=/   común
                                                                    └─> trusted/_control/{dataset}/{mes}.json    control
                                         Fallidos -> Catalogar (Punto 5) -> Hubo fallas -> Listo | Fallo
```

## Por qué así

| Decisión | Por qué | Descartado |
|---|---|---|
| **Dos salidas en la misma pasada:** el detalle por servicio y `viajes` | El detalle conserva todo lo de cada servicio (P3, P4, P5). `viajes` deja los tres servicios con las mismas columnas y las zonas unidas (P1, P2, P6), y evita repetir el UNION y el join en Athena, Hive, SparkSQL y PySpark | Solo una tabla unificada con cuarentena de filas malas: pierde columnas propias de cada servicio |
| **`viajes` materializada en Parquet** | Una vista de Athena solo existe en Athena. Hive en EMR y Spark no la ven, y las vistas multi-dialecto piden Lake Formation y roles que Academy no deja crear | Vista en el catálogo |
| **Las filas dudosas se marcan, no se borran** | raw y trusted tienen siempre las mismas filas, así se comprueba que no se perdió nada. Cada consulta filtra por las banderas que le importan | Cuarentena o borrado |
| **Un control propio por mes** en `trusted/_control/` | Se escribe al final, después de verificar los conteos. Un job caído deja el mes sin control, y la ejecución siguiente lo rehace | Comparar fechas de los part-files (unos archivos parciales parecerían un mes hecho); job bookmarks de Glue (son para DynamicFrames y un reset no limpia el destino) |
| **Overwrite de la ruta explícita de la partición** | Rehacer un mes reemplaza solo ese mes. Correrlo dos veces deja trusted igual | `partitionOverwriteMode=dynamic`: no aporta con una partición por corrida y EMR pide modo static para su committer optimizado |
| **Pendientes en una Lambda con `pendientes.py`** | Python puro con test. La ejecución automática, la manual y `--estado` calculan lo mismo | ASL puro con `listObjectsV2` y JSONata: fechas frágiles, paginación a mano, sin test local |
| **`repartition(n)` con n = ceil(bytes de raw / 256 MiB)** | 1 archivo por mes en green y yellow, 2 en HVFHV | `coalesce(n)`, que baja todo el stage a n tareas, también la lectura |
| **2 workers `G.1X` y un job a la vez** | AWS Academy restringe los recursos de Glue que se pueden usar a la vez y no publica los límites. Es la configuración que comprobamos estable. El mes más grande tarda menos de 4 min | Más workers y 3 meses en paralelo, como se planeó al principio |

Los workers y la concurrencia son dos valores en `RECURSOS` (`comun/config.py`). En una cuenta sin esas restricciones se suben sin tocar código.

## Zona trusted

```
s3://<bucket>/trusted/
  yellow/year=2024/month=01/part-*.parquet        detalle por servicio (también green/ y hvfhv/)
  viajes/servicio=yellow/year=2024/month=01/      común a los tres servicios
  taxi_zones/part-*.parquet                       sin partición
  _control/yellow/2024-01.json                    control del mes (no es una tabla)
  _control/taxi_zones.json
```

La partición es la del archivo de raw, no la fecha del pickup. `servicio`, `year` y `month` no son columnas del Parquet: salen de la ruta.

## Contrato y banderas

`contrato.py` define, por dataset, las columnas de raw, su nombre en trusted, el tipo y si son obligatorias. El job falla sin tocar trusted si un archivo trae una columna desconocida, le falta una obligatoria o un tipo cambia de familia (entero, decimal, texto, tiempo).
- Nombres en minúscula, y los tiempos de yellow y green renombrados como los de HVFHV (`pickup_datetime`, `dropoff_datetime`).
- `cbd_congestion_fee` no viene en los archivos de 2024 y se agrega como NULL, así los 24 meses tienen el mismo esquema.
- Columnas quitadas: solo las de auditoría que la ingesta agrega a green (`trip_id`, `mes_archivo`, `cargado_en`).
- Derivadas: `pickup_date`, `pickup_hour`, `duracion_min` y, en HVFHV, `espera_seg`.
- La tarifa de `viajes` va en componentes (`tarifa_base`, `recargos`, `peajes`, `propina`) más `cbd_fee` y `total_pagado`, para que P2 y P3 armen su métrica sin cambiar trusted.

| Bandera | Marca un viaje cuando… |
|---|---|
| `fuera_de_mes` | el pickup cae en otro mes que el del archivo |
| `duracion_invalida` | falta una fecha o el dropoff no es posterior al pickup |
| `distancia_invalida` | la distancia es nula o ≤ 0 |
| `monto_negativo` | algún componente de la tarifa es negativo |
| `zona_desconocida` | el origen o el destino es la zona 264 o 265 |
| `espera_negativa` (HVFHV) | el pickup es anterior a la solicitud |
| `pago_mayor_a_tarifa` (HVFHV) | `driver_pay` > `base_passenger_fare` |

## Cómo sabe qué falta (idempotencia)

Un par (dataset, mes) está pendiente si no tiene control o si su archivo de raw es más nuevo que el control. El job, en orden:
1. exige exactamente un Parquet en la partición de raw y valida su esquema contra el contrato;
2. borra el control del mes: de aquí en adelante, si algo falla el mes queda pendiente;
3. escribe el detalle, lo relee y compara el conteo con raw;
4. arma `viajes` desde el detalle escrito (join *broadcast* con las 265 zonas) y compara su conteo;
5. vuelve a mirar raw: si la ingesta lo reemplazó durante el job, no escribe el control;
6. escribe el control con los conteos, las banderas y el esquema.

## Encadenamiento

- **Automático:** al final de cada corrida, la Lambda `tlc-ingesta` llama `StartExecution` sobre `tlc-preparacion`, salvo que ya haya una ejecución en curso. No mira qué subió: la state machine calcula los pendientes y, si no hay, termina en segundos. Una regla de EventBridge directa a la state machine no sirve en Academy, porque `LabRole` no confía en `events.amazonaws.com`.
- **Fallas:** un mes que falla no frena a los demás. El `Map` anota el error y sigue, `Catalogar` registra lo que sí quedó y la ejecución termina en `Fallo`. El mes fallido sigue sin control, así que la ejecución siguiente lo reintenta. El job no reintenta por su cuenta (`MaxRetries=0`). Si Glue rechaza un job porque el anterior no ha liberado el cupo (`ConcurrentRunsExceededException`), el `Map` reintenta a los 30 s.
- **Plan B, manual:** `preparar_local.py --ejecutar` corre la misma state machine y espera a que termine, o espera la que ya esté en curso.

## Archivos

| Archivo | Qué hace |
|---|---|
| `contrato.py` | Esquema canónico, componentes de tarifa, derivadas, banderas y columnas de `viajes` |
| `pendientes.py` | Layout de trusted y cálculo de qué falta preparar |
| `preparar.py` | El Glue job: un mes de un dataset, de raw a trusted |
| `lambda_pendientes.py` | Primer estado de la state machine |
| `desplegar.py` | Publica el código y crea o actualiza el job, la Lambda y la state machine. `--borrar` los quita (trusted queda) |
| `preparar_local.py` | `--estado`, `--ejecutar` y `--forzar` (un mes o `--todo`) |
| `test_contrato.py`, `test_pendientes.py` | Tests sin AWS |

## Reproducir

Desde la raíz del repo, con raw cargada (Punto 3):

```bash
python punto4-preparacion/test_contrato.py && python punto4-preparacion/test_pendientes.py
python punto4-preparacion/desplegar.py                 # job, Lambda y state machine
python punto3-ingesta/desplegar.py                     # para que la ingesta encuentre la state machine
python punto4-preparacion/preparar_local.py --ejecutar # prepara todo lo pendiente (~4 h 41 min los 73)
python punto4-preparacion/preparar_local.py --estado   # 0 pendientes; exit 1 si raw y trusted no cuadran
```

Rehacer un mes: `preparar_local.py --forzar --dataset green --mes 2024-01`. Rehacer todo: `--forzar --todo`.

Al terminar la sesión: `python punto3-ingesta/desplegar.py --pausar` y `python punto2-fuentes/infra/apagar_infra.py`.

## Evidencias

Capturas del 2026-11-18 en la cuenta de la demo. En las de la consola se ocultaron el ID de la cuenta, el usuario y el sufijo del bucket.

| Figura | Qué muestra |
|---|---|
| [Glue](evidencias/punto4-1-glue-corridas.jpg) | El job `tlc-preparacion`: 150 corridas `Succeeded`, de a una (2 DPU, Glue 5.0) |
| [Step Functions](evidencias/punto4-2-state-machine-map.jpg) | La ejecución de la recarga completa (4 h 40 min, `Succeeded`), con el `Map` en la iteración 72 (yellow 2025-12) |
| [S3](evidencias/punto4-3-s3-trusted-viajes.jpg) | `trusted/viajes/servicio=yellow/year=2025/` con sus 12 particiones de mes |
| [`--estado`](evidencias/punto4-4-terminal-estado.png) | 0 pendientes y 73 controles, con raw = detalle = viajes en los tres servicios y el conteo de cada bandera |
| [Control](evidencias/punto4-5-terminal-control.png) | El control de yellow 2025-12: filas por capa, banderas, esquema y `job_run_id` |

## Resultados (2026-11-16)

Recarga completa con las dos salidas: una ejecución, 73 jobs de a uno, todos SUCCEEDED, en **4 h 41 min**. Unos 7,3 DPU-hora, cerca de **USD 3,2** (USD 0,44 por DPU-hora).

```
Pendientes: 0

Controles: 73
  dataset    meses     filas raw       detalle        viajes
  green         24     1,251,593     1,251,593     1,251,593
      distancia_invalida            59,012  (4.71%)
      duracion_invalida              2,572  (0.21%)
      fuera_de_mes                     412  (0.03%)
      monto_negativo                 3,961  (0.32%)
      zona_desconocida              17,820  (1.42%)
  hvfhv         24   483,060,132   483,060,132   483,060,132
      distancia_invalida            62,187  (0.01%)
      duracion_invalida             21,911  (0.00%)
      espera_negativa            5,106,777  (1.06%)
      fuera_de_mes                       0  (0.00%)
      monto_negativo                31,728  (0.01%)
      pago_mayor_a_tarifa       62,197,925  (12.88%)
      zona_desconocida          21,092,054  (4.37%)
  taxi_zones     1           265           265             0
  yellow        24    89,892,322    89,892,322    89,892,322
      distancia_invalida         2,179,263  (2.42%)
      duracion_invalida            559,814  (0.62%)
      fuera_de_mes                     634  (0.00%)
      monto_negativo             3,590,776  (3.99%)
      zona_desconocida             797,317  (0.89%)
```

- **Tiempos por mes:** green 1–2 min, yellow ~3 min, HVFHV ~6 min con `viajes`. Con 2 workers, HVFHV 2025-12 (22,1 M de filas, el más grande) tardó 227 s solo el detalle.
- **Zonas:** en green 2024-01 y HVFHV 2025-06, todos los viajes encontraron su zona en el join (`sin_zona` 0).
- **Idempotencia:** `--forzar` de yellow 2024-06 solo cambió su part-file y su control. Borrar el control de green 2024-03 y correr la ingesta rehízo solo ese mes, y una segunda invocación respondió "ya hay una ejecución en curso".
- **Camino de falla:** probado con `aws stepfunctions test-state` sobre la state machine desplegada: con un mes fallido, `Fallidos` lo separa y la ejecución termina en `Fallo`; sin fallas, en `Listo`.
- **Cobro por congestión:** con Athena (Punto 5), `cbd_fee` es NULL en todo 2024 y tiene valores en 2025.

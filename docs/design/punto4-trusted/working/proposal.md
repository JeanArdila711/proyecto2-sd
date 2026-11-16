## Propuestas

Pedido: Punto 4, preparación raw → trusted con AWS Glue y Apache Spark. Tiene que ser automática, encadenable con la ingesta y servir de base a los Puntos 5–7.
Research: `research.md` § Zona raw tal como está, § Requisitos, § Calidad de datos registrada, § Código existente, § Referencia de patrones, § AWS Glue, Step Functions y Academy, § Vacíos.

Restricciones que valen para las dos:
- Glue 5.0 con `G.1X`, que es lo único probado en Academy. `GlueVersion` va fijo, porque si no queda en 6.0 (research § AWS Glue).
- `LabRole` como rol del job y de la state machine. Confía en `glue` y en `states`, pero sus permisos solo se conocen probando.
- Recursos creados con un script boto3 idempotente, etiqueta `Project` y nombres en `comun/config.py` `RECURSOS`, que hoy no tiene claves de Glue (`comun/config.py:19-44`).
- Código publicado en `codigo/punto4-preparacion/` y directorio `punto4-preparacion/` (`punto4-preparacion/README.md:1-3`).
- 24 meses y unos 12,4 GiB. HVFHV manda en el dimensionamiento: 19–22 M filas por mes, entre 440 y 511 MiB por archivo.
- P2 y P3 siguen en Proposed (`docs/design/README.md:54-55`).

### Propuesta 1 — Tres tablas trusted, una por servicio, con todas las filas y banderas de calidad

- **Resumen:** un solo script PySpark de Glue, `preparar.py`, con un contrato de columnas por dataset. Cada corrida procesa un mes de un dataset y escribe `trusted/{yellow,green,hvfhv}/year=YYYY/month=MM/`, con la misma partición que tiene en raw. No se borra ninguna fila: cada regla de calidad agrega una columna booleana y los Puntos 6 y 7 deciden qué filtrar en cada pregunta. Las tarifas se pasan tipadas y con sus componentes separados; P2 y P3 se resuelven en las consultas, no en trusted.
- **Cambios clave:**
  - `punto4-preparacion/contrato.py`, Python puro sin Spark: el esquema canónico de cada dataset y las reglas de calidad. Se importa desde el job y desde el test.
    - Nombres en minúscula: `airport_fee` en los tres, `pulocationid`/`dolocationid` como int en todos.
    - `cbd_congestion_fee` double en los tres, en NULL donde no existe (2024 en yellow y HVFHV).
    - Fuera de green: `trip_id`, `mes_archivo` y `cargado_en`, que son auditoría de la ingesta (research § green).
  - `punto4-preparacion/preparar.py`, el Glue job (patrón de `m4-raw-to-structured/raw_to_structured.py:21-178`). Recibe `--dataset --mes --bucket`.
    - Lee la partición de raw, castea al contrato y falla si falta una columna obligatoria.
    - Deriva `pickup_date`, `pickup_hour`, `duracion_min` y, en HVFHV, `espera_seg = pickup − request`.
    - Banderas:
      - `fuera_de_mes`: pickup fuera del mes del archivo; yellow y green tienen pickups de 2002 a 2009 (research § Fechas fuera de mes).
      - `espera_negativa` (`findings.md:23-27`).
      - `pago_mayor_a_tarifa`: `driver_pay > base_passenger_fare` (`findings.md:26`).
      - `distancia_invalida`, `monto_negativo`.
    - Escribe con `coalesce` (1 archivo por mes; ~2–4 en HVFHV) y relee para comparar el conteo con el de raw.
  - `trusted/taxi_zones/` copiada y tipada, sin partición.
  - `punto4-preparacion/desplegar.py`, que sigue el patrón de upsert de `punto3-ingesta/desplegar.py:76-171`:
    - Crea o actualiza el Glue job (Glue 5.0, `G.1X`, número de workers por definir) y una state machine `tlc-preparacion`.
    - La state machine calcula qué meses de raw son más nuevos que su versión en trusted (comparando `LastModified`, igual que la ingesta "solo trae lo que falta"). Después usa `Map` con concurrencia acotada sobre `glue:startJobRun.sync`.
    - Disparo: la Lambda de ingesta inicia la state machine cuando terminó y subió algo; si no, la dispara una regla programada. Hay que decidirlo en el plan.
  - `punto4-preparacion/preparar_local.py`, para invocar y ver el estado (`--estado`, `--forzar --mes`), como `punto3-ingesta/ingestar.py:47-81`.
  - `comun/config.py` `RECURSOS`: nombres del job, de la state machine y de los prefijos `trusted/`.
- **Trade-offs:**
  - Se gana:
    - P2 y P3 no bloquean, porque las tarifas llegan completas y tipadas.
    - No se pierde ninguna fila: las banderas son evidencia de calidad que se muestra en la sustentación y se audita con SQL.
    - La partición coincide con la de raw, así que reprocesar un mes reemplaza exactamente una partición. Eso es idempotente y determinista.
    - El Punto 5 cataloga cuatro tablas con un esquema estable.
  - Se arriesga:
    - P1 y P6 tienen que hacer `UNION ALL` de tres tablas en los Puntos 6 y 7.
    - Cada consulta tiene que acordarse de filtrar las banderas.
    - Las filas de pickup fuera del mes quedan en la partición del archivo, no en la de su fecha real.
- **Validación:**
  - `test_contrato.py` sin pytest (estilo de `punto3-ingesta/test_raw.py`): el contrato cubre todas las columnas de raw de cada dataset y los nombres canónicos son únicos.
  - Correr green 2024-01, que es chico, y comparar conteos y esquema. Después HVFHV 2025-12, el más grande, para dimensionar workers y medir tiempo.
  - Correr los 72 meses por la state machine y repetirla: la segunda corrida no lanza ningún job.
  - Hacer `--forzar` de un mes y confirmar que se reemplaza solo esa partición.
  - Validar con Athena, o en el Punto 5, que la suma de filas de trusted es igual a la de raw.
- **Preguntas abiertas:**
  - Si `LabRole` puede crear el job y la state machine y usar `startJobRun.sync`: se descubre en la primera corrida.
  - Cuántos workers necesita HVFHV, y qué cuesta.
  - Cuál de los dos disparos: encadenar desde la Lambda o usar una regla propia.
  - Si los Puntos 6 y 7 quieren una vista unificada encima de las tres tablas. Se puede crear en el Punto 5 sin tocar trusted.

### Propuesta 2 — Una tabla `viajes` unificada, con las filas malas en cuarentena

- **Resumen:** un Glue job que lee los tres servicios de un mes y los mapea a una sola tabla `trusted/viajes/servicio=X/year=YYYY/month=MM/`.
  - El esquema es común: `servicio`, `compania`, `pickup_ts`, `dropoff_ts`, `pu_zona`, `do_zona`, `pu_borough`, `do_borough`, `millas`, `tarifa_base`, `recargos`, `propina`, `cbd_fee`, `pago_conductor` y `espera_seg`. Lo propio de un servicio queda en NULL en los demás.
  - Las zonas se desnormalizan con un join a `taxi_zones`.
  - Las filas que no pasan una regla salen de trusted a `trusted/_rechazados/` con el motivo, al estilo de la cuarentena de `m4-landing-to-raw/lambda_function.py:227-303`.
  - La partición se arma con el mes del pickup, porque las filas fuera de mes se rechazan.
- **Cambios clave:**
  - `punto4-preparacion/contrato.py`: el mapeo de cada dataset al esquema común. Por ejemplo, qué es `tarifa_base` en yellow (`fare_amount`) frente a HVFHV (`base_passenger_fare`), y qué entra en `recargos`.
  - `punto4-preparacion/preparar.py`: un solo job por mes que procesa los tres datasets, hace el join con las zonas, aplica las reglas y separa los rechazados.
  - `desplegar.py` y la state machine iguales a la propuesta 1, pero con un job por mes en lugar de uno por mes y dataset.
- **Trade-offs:**
  - Se gana:
    - P1 y P6 salen de una sola tabla, sin UNION ni join a zonas.
    - Las consultas de los Puntos 6 a 8 son más cortas.
    - Trusted queda "limpio" en el sentido estricto.
  - Se arriesga:
    - **El mapeo de tarifas es justo P2 y P3.** Fijar `tarifa_base` y `recargos` ahora es decidir esas preguntas en trusted, y si David las define distinto hay que reprocesar los 72 meses.
    - Rechazar filas cambia el resultado de P3: los viajes con `driver_pay` mayor que la tarifa son el 7–16 %, y eso es un hallazgo, no basura.
    - Las particiones dejan de calzar con raw, porque los rechazados fuera de mes van a otra parte. Reprocesar un mes ya no reemplaza una sola partición.
    - Un job por mes que mezcla HVFHV con lo demás pesa más y, si falla, hay que repetir todo el mes.
    - Una tabla ancha con columnas en NULL por servicio.
- **Validación:**
  - Test del mapeo: cada columna común tiene origen en cada servicio o es NULL a propósito.
  - Conteo: filas en `viajes` + filas en `_rechazados` = filas en raw, por mes y servicio.
  - Las mismas corridas de prueba e idempotencia de la propuesta 1.
- **Preguntas abiertas:**
  - Requiere cerrar P2 y P3 antes de implementar.
  - Qué reglas rechazan y cuáles solo marcan.
  - Cómo se reprocesa un mes cuyos rechazados quedaron en otra partición.

### Combinación (1 + 2): tres tablas por servicio y una tabla unificada, generadas en la misma pasada

Pedida por Jean después de leer las dos propuestas. Toma de la 1 lo que protege contra P2 y P3, y de la 2 la tabla unificada y las zonas desnormalizadas. Deja afuera la cuarentena de filas.

- **Resumen:** el mismo job de la propuesta 1 (`preparar.py`, un mes de un dataset por corrida) escribe dos salidas en una sola pasada. Las dos quedan particionadas igual que raw, así que reprocesar un mes reemplaza exactamente una partición en cada salida.
  1. **`trusted/{yellow,green,hvfhv}/year=/month=`**, la capa de detalle.
     - Todas las columnas de la fuente, con nombres y tipos canónicos y `cbd_congestion_fee` en NULL en 2024.
     - Las columnas derivadas y las banderas de calidad de la propuesta 1.
     - Ninguna fila se borra.
     - Aquí van las preguntas que necesitan columnas propias de un servicio: P3 (`driver_pay`), P4 (`request_datetime`) y P5 (`payment_type`, `RatecodeID`).
  2. **`trusted/viajes/servicio=/year=/month=`**, la capa común y angosta. Es una proyección de la anterior con las columnas que tienen sentido en los tres servicios:
     - Identidad y tiempos: `servicio`, `compania` (`yellow`, `green`, `uber`, `lyft`), `pickup_ts`, `dropoff_ts`, `pickup_date`, `pickup_hour`.
     - Zonas: `pu_zona_id`, `pu_zona`, `pu_borough`, `pu_service_zone` y lo mismo para `do_`. Salen de un join broadcast con las 265 filas de `taxi_zones`.
     - Montos: `millas`, `tarifa_base`, `recargos`, `peajes`, `propina`, `cbd_fee`, `total_pagado`.
     - Las banderas de calidad.
     - Aquí van P1, P2 y P6.
- **Cómo se evita decidir P2 y P3 en trusted:** la tarifa no se guarda como un solo número. Va separada en componentes que se pueden sumar, y cada consulta arma la definición que elija David:
  - `tarifa_base`: `fare_amount` en yellow y green, `base_passenger_fare` en HVFHV.
  - `recargos`: en yellow y green, `extra + mta_tax + improvement_surcharge + congestion_surcharge + airport_fee + cbd_congestion_fee`; en HVFHV, `bcf + sales_tax + congestion_surcharge + airport_fee + cbd_congestion_fee`.
  - `peajes` y `propina`, aparte.
  - "Tarifa base" es `tarifa_base`, y "con recargos" es `tarifa_base + recargos`, con o sin `peajes`. El denominador de P3 sale de los mismos componentes en `trusted/hvfhv`.
  - El mapeo de `recargos` es mecánico: suma columnas con el mismo significado. No elige ninguna de las opciones de P2.
- **Calidad: se marca, no se rechaza.** Las filas que la propuesta 2 mandaba a cuarentena se quedan con su bandera. Lo único que corta el job es un archivo que no cumple el contrato: falta una columna obligatoria o un tipo no se puede castear. En ese caso el job falla, no escribe nada y la partición anterior de trusted queda intacta.
- **Por qué materializar `viajes` y no dejarlo como vista:** el Punto 6 consulta con Athena, Hive y SparkSQL. Una vista creada en Athena se guarda en el Data Catalog con SQL de Trino, y según lo que recuerdo Hive y Spark no la pueden leer. *Sin verificar*: confirmarlo en el plan. Una tabla en Parquet funciona igual en los tres motores, y como sale de la misma pasada, no cuesta otro job.
- **Orquestación:**
  - State machine `tlc-preparacion`: calcula qué pares (dataset, mes) de raw son más nuevos que su versión en trusted y hace un `Map` con concurrencia acotada sobre `glue:startJobRun.sync`. Aparte, un paso copia y tipa `taxi_zones` cuando cambia.
  - Disparo: al final de cada corrida, la Lambda `tlc-ingesta` inicia la state machine si subió algo. Así raw → trusted queda encadenado sin esperar a un reloj.
  - El cálculo de "qué falta" se hace en la state machine y no lo pasa la Lambda. Por eso una corrida manual (`preparar_local.py`) o un reintento ven exactamente lo mismo, y cualquier ejecución es idempotente.
- **Cambios clave:**
  - En `punto4-preparacion/`:
    - `contrato.py`: esquemas canónicos por dataset, el mapeo a `viajes`, los componentes de tarifa y las reglas de calidad. Es Python puro, sin Spark.
    - `preparar.py`: el Glue job con las dos salidas.
    - `desplegar.py`: el job, la state machine y el permiso de la Lambda para iniciarla.
    - `preparar_local.py`: `--estado`, `--forzar --dataset --mes` y la ejecución manual.
    - `test_contrato.py`.
    - `README.md`.
  - `punto3-ingesta/lambda_ingesta.py`: al final del handler, `states:StartExecution` si `resumen` trae archivos nuevos. Si falla, solo se registra el error y no se tumba la ingesta (mismo criterio de `lambda_ingesta.py:162`).
  - `comun/config.py` `RECURSOS`: nombres del job, de la state machine y de los prefijos.
- **Trade-offs:**
  - Se gana:
    - P1, P2 y P6 salen de una tabla, y P3, P4 y P5 de la tabla de su servicio.
    - P2 y P3 no bloquean.
    - No se pierde ninguna fila.
    - Las particiones coinciden con raw en las dos salidas, así que el reproceso es idempotente.
    - El pipeline queda encadenado de punta a punta: EventBridge → ingesta → preparación.
  - Se arriesga:
    - Los datos de las columnas comunes quedan escritos dos veces. `viajes` es angosta, así que el costo es menor que la capa de detalle (*sin medir*).
    - El esquema de `viajes` es un contrato más que mantener.
    - La Lambda de ingesta necesita `states:StartExecution`, que con `LabRole` no está verificado.
    - Las filas con pickup fuera de mes quedan en la partición del archivo; las consultas las excluyen con su bandera.
- **Validación:**
  - `test_contrato.py`:
    - Cada columna de raw tiene destino en el contrato.
    - Cada columna de `viajes` tiene origen en los tres servicios o es NULL a propósito.
    - Los componentes de `recargos` existen en su dataset.
  - Corrida de green 2024-01. Comparar filas de raw, `trusted/green` y `trusted/viajes/servicio=green`, y revisar que `pu_borough` no quede NULL salvo en las zonas 264 y 265 (*sin verificar* que esas sean las "Unknown").
  - HVFHV 2025-12, para dimensionar workers y medir el tiempo.
  - Carga completa por la state machine y una segunda ejecución que no lance ningún job.
  - Un `--forzar` sobre un mes y confirmar que solo se reemplazan sus dos particiones.
  - Encadenamiento: liberar un mes con `simular.py --forzar` y ver que llega solo hasta trusted.
- **Preguntas abiertas:**
  - Permisos de `LabRole` para Glue, Step Functions y `states:StartExecution` desde la Lambda.
  - Cuántos workers necesita y cuánto cuesta.
  - Si Hive y Spark leen vistas de Athena, para confirmar la decisión de materializar.
  - Cuáles son las zonas "Unknown" en `taxi_zones` (LocationID 264 y 265, *sin verificar*).

## Dirección elegida
La combinación (1 + 2), aprobada por Jean el 2026-11-15, con dos ajustes:
1. **Construcción en dos capas.** Primero la capa de detalle por servicio, `trusted/{yellow,green,hvfhv}`, con el job, la state machine y las pruebas. Después se agrega `trusted/viajes` como segunda salida del mismo job. La capa de detalle sola ya cumple el Punto 4.
2. **Disparo desde la Lambda de ingesta con `states:StartExecution`.** La trust policy de `LabRole` no incluye `events.amazonaws.com`, así que una regla de EventBridge que apunte directo a la state machine no tiene un rol que asumir. Si `LabRole` no permite el disparo desde la Lambda, el plan B es ejecutarla a mano con `preparar_local.py`. Es lo primero que se prueba en AWS.

Razón, en palabras de la discusión: `viajes` cuesta poco porque sale de la misma pasada, y evita repetir el UNION y el join con zonas en los cuatro motores de los Puntos 6 y 7. Las tarifas por componentes y las banderas de calidad mantienen a P2 y P3 sin bloquear.

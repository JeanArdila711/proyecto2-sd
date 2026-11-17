# Review: punto4-trusted
Fecha: 2026-11-16 · HEAD: f100c0e · Base del plan: dff07ac · Árbol de trabajo limpio: se revisó `git diff dff07ac HEAD` (código de `punto4-preparacion/`, `comun/config.py`, `punto3-ingesta/`).

## Resumen
Las fases 0 a 5 están completas y la lógica es correcta. No encontré nada que haya que arreglar antes de entregar. Falta la fase 6 (README, evidencias, tarea 3.3) y queda un camino de la state machine sin probar en AWS: el de los meses fallidos.

## Verificación
- `.venv/bin/python punto4-preparacion/test_contrato.py` → ok
- `.venv/bin/python punto4-preparacion/test_pendientes.py` → ok
- `.venv/bin/python punto3-ingesta/test_raw.py` → ok (sin regresión)
- `.venv/bin/python punto5-catalogo/test_catalogo.py` → ok
- `grep -rnE '[0-9]{12}' punto4-preparacion/` → sin resultados
- No hay lint ni typecheck configurados (no hay `pyproject.toml`, y `pyflakes` no está en `.venv`).
- Las verificaciones en AWS (fases 1 a 5, recarga de 72 meses, `--estado` con exit 0) están registradas en las notas del plan. No las repetí: la cuenta tiene que estar encendida y cada corrida cuesta.

## Contra el plan
- Tareas: 0.x, 1.x, 2.x, 3.1, 3.2, 4.x y 5.x hechas. Faltan **3.3, 6.1 y 6.2**: `punto4-preparacion/README.md` todavía dice "Pendiente" y no existe `evidencias/`.
- Las dos verificaciones automáticas de la fase 0 siguen sin marcar. Ya no aplican, porque los recursos `tlc-prueba-*` estaban en la cuenta desactivada. Conviene marcarlas como N/A.
- Desvíos documentados en las notas, todos razonables: se borra el control antes de escribir, se relee raw al final, `Catch` por mes, `viajes` sale del detalle escrito, `servicio` va solo en la ruta, `cbd_fee` sin `coalesce`, y 2 workers con concurrencia 1.
- Desvío que no está en las notas: `punto4-preparacion/desplegar.py` ganó el estado `Catalogar` y la opción `--solo-state-machine` en el commit del Punto 5 (f100c0e). Lo respalda la convención "Catalogación", pero el plan del Punto 4 no lo menciona.
- No se tocó nada de "NO se tocan" ni de "Fuera de alcance".

## Revisión del código
Lo que revisé y está bien:
- **Qué falta preparar** (`pendientes.py`). Un mes queda pendiente si su control no existe o es más viejo que raw. Como el control se borra antes de escribir, un job que se cae deja el mes pendiente. El orden es determinista y está probado.
- **Escritura** (`preparar.py:100-121`). Overwrite en la ruta explícita de la partición. El conteo se compara contra lo releído, en detalle y en viajes.
- **Carrera con la ingesta.** El archivo de raw se vuelve a leer antes de escribir el control (`preparar.py:125`), y cualquier escritura en S3 es atómica.
- **Concurrencia** (`desplegar.py:54`, `:140`). Aunque coincidan dos ejecuciones, `MaxConcurrentRuns=1` en el job hace que Glue rechace la segunda corrida. Así se cumple la regla de un solo job a la vez aunque falle el chequeo de la Lambda.
- **Banderas y montos.** `coalesce(..., false)` en las banderas. `monto_negativo` da bien con componentes NULL. `total_pagado` de HVFHV coincide con el denominador de la convención "Métrica de P3".
- **Fechas.** Con `spark.sql.session.timeZone=UTC`, el cast de `timestamp_ntz` a `timestamp` conserva la hora de pared de NY, y `fuera_de_mes`, `pickup_hour` y `pickup_date` salen deterministas.
- **Encadenamiento** (`lambda_ingesta.py:158-178`). Si el disparo falla, no tumba la ingesta, y usa timeouts cortos.

## Acciones
1. 🟡 Fase 6 completa en `punto4-preparacion/README.md:1-3`: diagrama, "Por qué así", layout, contrato y banderas, idempotencia, Reproducir, Evidencias y Resultados (tarea 3.3 incluida), más las capturas en `punto4-preparacion/evidencias/`. Es lo que pide la rúbrica para el punto.
2. 🟡 El camino de falla de la state machine no está probado en AWS (`punto4-preparacion/desplegar.py:123`, `:148-172`). En la recarga no falló ningún job, así que nunca corrieron `Catch` → `Anotar falla` → `Fallidos` (`$[?(@.error)]`) → `Hubo fallas` → `Fallo`. Una prueba barata, sin Glue: `aws stepfunctions test-state` sobre el estado `Fallidos` con un input de dos ítems, uno con `error`, para confirmar que devuelve `{"fallidos": [ítem con error]}`. *Sin verificar* que `LabRole` permita `TestState`. Si no lo permite, decirlo en el README como límite conocido.
3. 🟢 `comun/config.py:48-49`: `trusted_prefijo` y `control_prefijo` no los usa nadie. Las rutas reales están en `pendientes.py:13-15` (`TRUSTED`, `CONTROL`). Si alguien cambia uno sin el otro, divergen. Conviene borrar las dos claves.
4. 🟢 `punto3-ingesta/lambda_ingesta.py:170-172`: el comentario dice que con dos ejecuciones a la vez "dos jobs pueden reescribir la misma partición". Con `MaxConcurrentRuns=1` eso no pasa: la segunda corrida espera con el `Retry` o falla con `ConcurrentRunsExceeded`. A lo sumo un mes se rehace dos veces, en serie. Ajustar el comentario.
5. 🟢 Ordenar el plan: marcar como N/A las verificaciones automáticas de la fase 0 y anotar el desvío del estado `Catalogar` y de `--solo-state-machine`.

No es un cambio sensible (auth, pagos, datos personales o migraciones), así que no hace falta una segunda revisión con otra familia de modelos. Sin 🔴: el siguiente paso es la fase 6, no `/reppit-implement`.

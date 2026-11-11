# Proyecto 2 Big Data TLC — Findings

Hechos durables que sirven a otros topics. Un bloque por finding, solo con contraste reutilizable: algo que costó descubrir o que se hizo de dos formas con resultados distintos. Se carga solo cuando la tarea toca un tema listado acá. Pasadas unas 150 líneas, se parte en `findings/{tema}.md`.

## [hecho] Esquema: `cbd_congestion_fee` no existe en los archivos de 2024

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** la columna aparece desde 2025 (el cobro arranca el 5 de enero de 2025) en yellow, green y HVFHV. En 2024 está ausente, no en null. Cualquier contrato de esquema, ingesta o tabla que cubra los dos años tiene que tolerar la columna faltante.
- **Provenance:** footers de `{yellow,green,fhvhv}_tripdata_2024-06` y `2025-06` leídos por range request; texto de la página de datos de la TLC.

## [hecho] HVFHV: en 2024–2025 solo hay Uber (HV0003) y Lyft (HV0005)

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** conteo completo de `hvfhs_license_num`: 2024-01 → Uber 14,43 M, Lyft 5,23 M; 2025-12 → Uber 15,97 M, Lyft 6,13 M. Via (HV0004) y Juno (HV0002), que lista el diccionario, ya no aparecen. Lo que se modele por compañía tiene dos valores.
- **Provenance:** lectura de la columna en `fhvhv_tripdata_2024-01` y `2025-12` (sesión 2026-11-10).

## [hecho] Propinas: `tip_amount` solo registra las pagadas con tarjeta

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** según el diccionario de yellow (2025-03-18), las propinas en efectivo no se registran. Todo análisis de propinas en taxis se filtra a `payment_type = 1`; promediar sobre todos los pagos subestima la propina.
- **Provenance:** `data_dictionary_trip_records_yellow.pdf`.

## [hecho] Calidad HVFHV: esperas negativas y pagos al conductor mayores que la tarifa base

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** en el row group 0 de junio, entre 2.451 y 6.636 viajes por compañía tienen `pickup_datetime < request_datetime`. Además, `driver_pay > base_passenger_fare` en ≈ 12–16 % de los viajes de Uber y ≈ 7–8 % de los de Lyft. La capa trusted tiene que filtrar o marcar las esperas negativas, y la comparación `driver_pay / base_passenger_fare` puede dar más de 100 %.
- **Provenance:** row group 0 de `fhvhv_tripdata_2024-06` y `2025-06` (sesión 2026-11-10).

## [hecho] Volumen: HVFHV es el 88 % de los datos

- **Date:** 2026-11-10 · **Source topic:** `planificacion`
- **Finding:** de 12,38 GiB en 72 archivos (2024–2025), HVFHV ocupa 10,93 GiB, con archivos de hasta 511 MiB (unos 20 M de filas al mes). Yellow pesa 1,42 GiB y green unos 13 MiB. El dimensionamiento (timeouts de ingesta, workers de Glue o EMR) lo define HVFHV.
- **Provenance:** `HEAD` a los 72 archivos en CloudFront (sesión 2026-11-10).

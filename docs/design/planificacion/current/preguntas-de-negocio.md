# Preguntas de negocio y datos

Escogidas por Jean el 2026-11-10. Las seis se responden solo con datos publicados por la TLC (convención "Solo datos TLC" en `CONTEXT.md`).

Fuentes revisadas: la [guía de usuario](https://www.nyc.gov/assets/tlc/downloads/pdf/trip_record_user_guide.pdf) (última actualización 2019), la [página de datos](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page) y los diccionarios de yellow, green y High Volume FHV (versión del 18 de marzo de 2025).

## Preguntas

| # | Pregunta | Datos |
|---|---|---|
| P1 | ¿Cuál es la participación de mercado de taxis amarillos, verdes, Uber y Lyft por borough y por mes? | yellow + green + HVFHV + zonas |
| P2 | ¿Cuánto cuesta la milla en taxi amarillo frente a Uber y Lyft, por zona y por hora? | yellow + HVFHV + zonas |
| P3 | ¿Qué porcentaje de lo que paga el pasajero le llega al conductor en Uber y en Lyft, y cómo varía por hora y borough? | HVFHV + zonas |
| P4 | ¿Cuánto espera un pasajero desde que pide el viaje hasta que lo recogen, por compañía, borough y hora? | HVFHV + zonas |
| P5 | ¿Qué se asocia a propinas más altas en taxi amarillo: hora, distancia, zona de origen o viaje al aeropuerto? | yellow (solo `payment_type = 1`) + zonas |
| P6 | ¿Cambió el cobro por congestión (desde el 5 de enero de 2025) la cantidad de viajes hacia la zona de cobro y el reparto entre taxis y apps? | yellow + green + HVFHV 2024 y 2025 + zonas |

### Campos que usa cada una
- **P1:** conteo de filas por dataset; `hvfhs_license_num` (HV0003 = Uber, HV0005 = Lyft); `PULocationID` → `Borough`.
- **P2:** `fare_amount / trip_distance` (yellow) frente a `base_passenger_fare / trip_miles` (HVFHV); hora de pickup; `PULocationID`.
- **P3:** `driver_pay` frente a `base_passenger_fare` u otro denominador (abierto); hora; borough.
- **P4:** `pickup_datetime − request_datetime`. `on_scene_datetime` no sirve porque solo se llena en vehículos accesibles.
- **P5:** `tip_amount`, `payment_type = 1`, hora, `trip_distance`, `PULocationID`, `RatecodeID` / `airport_fee` / zonas con `service_zone = Airports` o `EWR`.
- **P6:** `DOLocationID` → zonas de cobro (derivadas de 2025, convención "Zonas de cobro por congestión"); conteos 2024 contra 2025 por servicio; `cbd_congestion_fee` solo en 2025.

## Puntos abiertos
- **P2:** los componentes de la tarifa no son iguales entre datasets. Hay que definir qué se compara (`fare_amount` frente a `base_passenger_fare`, con o sin recargos).
- **P3:** definir el denominador: tarifa base, o todo lo que paga el pasajero (base + peajes + impuestos + recargos + propina).

## Datos

| Dataset | Qué es | 2024 | 2025 |
|---|---|---|---|
| Yellow | Taxis amarillos; únicos que recogen en la calle en los 5 boroughs | 0,65 GiB | 0,77 GiB |
| Green | Taxis verdes; recogen en la calle solo encima de W 110 St / E 96 St en Manhattan y en los boroughs | ~6 MiB | ~7 MiB |
| HVFHV | Uber y Lyft | 5,38 GiB | 5,55 GiB |
| Taxi Zone Lookup (CSV) | 265 filas: `LocationID`, `Borough`, `Zone`, `service_zone` | — | — |

- **Total:** 72 archivos parquet, 12,38 GiB. El más grande es `fhvhv_tripdata_2025-12`, con 511 MiB. Medido con `HEAD` a CloudFront el 2026-11-10.
- **URLs:** `https://d37ci6vzurychx.cloudfront.net/trip-data/{dataset}_tripdata_{YYYY-MM}.parquet` con `dataset` ∈ {`yellow`, `green`, `fhvhv`}. Zonas: `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv`. Shapefile de zonas: `https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip`.
- **Filas por mes (junio):** HVFHV 20,1 M (2024) y 19,9 M (2025); yellow 3,5 M y 4,3 M; green 55k (2024).
- **Publicación:** cada mes, con unos dos meses de rezago. La guía de usuario de 2019 dice CSV y publicación semestral; eso ya no aplica.
- Las advertencias de calidad y esquema están en `findings.md`.

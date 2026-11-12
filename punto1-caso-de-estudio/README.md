# Punto 1 — Caso de estudio y preguntas de negocio

## Caso de estudio

Analizamos los viajes en taxi y en aplicaciones de transporte (Uber y Lyft) en Nueva York durante 2024 y 2025, con los registros que publica la NYC Taxi and Limousine Commission (TLC). El objetivo es entender cómo compiten los taxis tradicionales (amarillos y verdes) con Uber y Lyft: quién se queda con los viajes en cada borough, cuánto cuesta moverse en cada servicio, cuánto recibe el conductor, cuánto espera el pasajero, de qué dependen las propinas y qué efecto tuvo el cobro por congestión que empezó el 5 de enero de 2025. Todo se responde solo con datos publicados por la TLC.

## Datos

| Conjunto | Contenido | 2024 | 2025 |
|---|---|---|---|
| Yellow Taxi Trip Records | Taxis amarillos (Parquet mensual) | 0,65 GiB | 0,77 GiB |
| Green Taxi Trip Records | Taxis verdes (Parquet mensual) | ~6 MiB | ~7 MiB |
| High Volume FHV Trip Records | Uber (`HV0003`) y Lyft (`HV0005`) (Parquet mensual) | 5,38 GiB | 5,55 GiB |
| Taxi Zone Lookup | 265 zonas: `LocationID`, `Borough`, `Zone`, `service_zone` (CSV) | — | — |

72 archivos Parquet y 12,38 GiB en total. Fuente: [TLC Trip Record Data](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page).

## Preguntas de negocio

1. ¿Cuál es la participación de mercado de los taxis amarillos, los taxis verdes, Uber y Lyft por borough y por mes?
2. ¿Cuánto cuesta la milla en taxi amarillo frente a Uber y Lyft, por zona y por hora?
3. ¿Qué porcentaje de lo que paga el pasajero le llega al conductor en Uber y en Lyft, y cómo varía por hora y por borough?
4. ¿Cuánto espera un pasajero desde que pide el viaje hasta que lo recogen, por compañía, borough y hora?
5. ¿Qué se asocia a propinas más altas en taxi amarillo: la hora, la distancia, la zona de origen o que el viaje vaya al aeropuerto?
6. ¿Cambió el cobro por congestión, vigente desde el 5 de enero de 2025, la cantidad de viajes hacia la zona de cobro y el reparto entre taxis y aplicaciones?

Los campos que usa cada pregunta y las consideraciones de calidad de datos están en el documento de entrega (Punto 1).

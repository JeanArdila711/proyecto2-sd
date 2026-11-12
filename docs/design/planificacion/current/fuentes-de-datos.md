# Fuentes de datos (Punto 2)

Decidido por David el 2026-11-11. El veredicto vive en `CONTEXT.md` § Conventions ("Fuentes de datos"); este documento tiene el detalle.

## Reparto

| Fuente | Qué contiene | Volumen | Recurso (límites en `findings.md`) |
|---|---|---|---|
| **RDS MariaDB** | Tabla `taxi_zones` (Taxi Zone Lookup) y tabla `green_trips` (viajes de green 2024–2025) | 265 filas + ~1,3 M filas | `db.t3.micro`, 20 GB |
| **Archivos en EC2** | Los 24 Parquet mensuales de yellow 2024–2025, tal como los publica la TLC, en una carpeta del disco de la instancia | 1,42 GiB | `t3.small` o `t3.medium` con `LabInstanceProfile` |
| **URL en Internet** | Los 48 Parquet de HVFHV (Uber y Lyft) directo de CloudFront de la TLC | 10,93 GiB | — |

Por qué así:
- **La base de datos no es decorativa:** las seis preguntas cruzan con `taxi_zones` (borough, zona, aeropuertos) y P1 y P6 además usan `green_trips`.
- **Cada fuente con su tamaño:** pocas filas en la base de datos (como un sistema transaccional), volumen medio en el servidor de archivos y lo masivo (88 %) directo de Internet, sin copias intermedias.
- **Tres técnicas de ingesta distintas** para el Punto 3: consulta SQL, copia de archivos y descarga HTTP.

Preguntas por fuente:

| Pregunta | RDS | EC2 | URL |
|---|---|---|---|
| P1 | green + zonas | yellow | HVFHV |
| P2 | zonas | yellow | HVFHV |
| P3 | zonas | — | HVFHV |
| P4 | zonas | — | HVFHV |
| P5 | zonas | yellow | — |
| P6 | green + zonas | yellow | HVFHV |

## Siembra y simulador

- **Siembra (seed):** script reproducible que crea el esquema en MariaDB, carga `taxi_zones` y deja la EC2 con la carpeta de yellow. Va en el directorio del Punto 2 del repo, con instrucciones.
- **Simulador de llegada de datos:** libera un mes a la vez en las tres fuentes: inserta las filas de green de ese mes en MariaDB, deja el Parquet de yellow de ese mes en la EC2 y habilita ese mes de HVFHV para descarga. La ingesta automática (Punto 3) detecta lo nuevo y lo sube a S3 sin intervención. Sirve para mostrar la automatización en vivo en la sustentación, porque 2024–2025 ya están publicados completos.

## Puntos abiertos

- **Extracción desde RDS hacia S3:** primero Glue con conexión JDBC (la rúbrica nombra Glue). Requiere VPC: security group autorreferenciado y endpoint de S3, no probados en Learner Lab. Plan B: script Python con cron en la EC2. Se decide en el diseño de la ingesta (Punto 3).
- **Formato de yellow en EC2:** Parquet tal como lo publica la TLC (recomendado; CSV pesaría ~8–10 GB y añade un paso de conversión). Pendiente de confirmar al implementar.
- **Opcional:** el shapefile de zonas (`taxi_zones.zip`, dato TLC) en la EC2, para mapas en el Punto 8.

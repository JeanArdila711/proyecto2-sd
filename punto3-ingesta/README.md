# Punto 3 — Ingesta automática al datalake

Las tres fuentes del [Punto 2](../punto2-fuentes/) llegan solas a la zona **raw** del bucket. Cada 5 minutos, una regla de EventBridge invoca una Lambda que trae solo lo que falta. Cuando el simulador libera un mes nuevo, en la corrida siguiente aparece en S3 sin que nadie haga nada.

```
EventBridge (cada 5 min)
   └─> Lambda tlc-ingesta ──── HVFHV: URL de la TLC ──── streaming ──> s3://<bucket>/raw/hvfhv/
              │
              └─ SSM Run Command ─> EC2 tlc-fuente-archivos (ec2_ingesta.py)
                                     ├─ /data/tlc/yellow ──────────────> raw/yellow/
                                     └─ RDS MariaDB (privada)
                                         ├─ green_trips por mes ───────> raw/green/
                                         └─ taxi_zones ────────────────> raw/taxi_zones/
```

## Por qué así

| Fuente | Quién la ingiere | Por qué |
|---|---|---|
| URL (HVFHV, 88 % del volumen) | La Lambda, con descarga por streaming de CloudFront a S3 (subida multiparte, sin disco) | Es una descarga HTTP. La Lambda aguanta 15 minutos y en las pruebas un archivo de ~480 MiB tardó unos 7 s |
| Archivos de la EC2 (yellow) | Un script en la misma EC2, lanzado por SSM | Una Lambda no puede leer el disco de una instancia |
| RDS MariaDB (green, zonas) | El mismo script en la EC2 | La RDS es privada y la EC2 ya llega a ella. Una Lambda o un Glue JDBC tendrían que entrar a la VPC (endpoint de S3, security group autorreferenciado), y eso no estaba probado en Learner Lab |

Lo que se descartó:
- **Airflow.** La rúbrica no lo pide. Habría que montar otra EC2 (MWAA no está verificado en Academy) y mantenerla encendida.
- **Glue JDBC** para la RDS. Ver la tabla de arriba.

## Zona raw

Un prefijo por dataset y un Parquet por mes, con particiones estilo Hive. Así el crawler de Glue, Athena y Spark leen `year` y `month` como columnas y solo abren los meses que piden.

```
s3://proyecto2-tlc-<sufijo>/raw/
  yellow/year=2024/month=01/yellow_tripdata_2024-01.parquet
  green/year=2024/month=01/green_tripdata_2024-01.parquet
  hvfhv/year=2024/month=01/fhvhv_tripdata_2024-01.parquet
  taxi_zones/taxi_zones.parquet
```

Las rutas se definen una sola vez, en [`raw.py`](raw.py). Yellow y HVFHV se guardan tal como los publica la TLC. Green y `taxi_zones` salen de MariaDB a Parquet con los tipos del esquema de la tabla, no de los valores: `cbd_congestion_fee`, que en 2024 es todo NULL, queda como `double` en todos los meses. El Parquet de green también lleva las columnas de auditoría de la fuente (`trip_id`, `mes_archivo`, `cargado_en`).

## Cómo sabe qué falta (idempotencia)

Cada corrida compara la fuente con lo que ya está en raw. Correrla dos veces no duplica nada, y reingerir un mes reemplaza su archivo.

| Dataset | Se sube cuando… | Verificación |
|---|---|---|
| HVFHV | el mes está entre 2024-01 y el reloj simulado (`/proyecto2-sd/simulacion/mes_actual`) y no está en raw | el tamaño en S3 coincide con el `Content-Length` de la TLC; si no, se borra y se marca error |
| yellow | el archivo está en `/data/tlc/yellow` y en raw no existe o tiene otro tamaño | filas del footer del Parquet en los metadatos del objeto (`filas`) |
| green | el mes está en `cargas_green` y en raw no existe o tiene otro `cargado_en`. Un `simular.py --forzar` cambia esa fecha y el mes se vuelve a extraer | las filas extraídas se cuadran contra `cargas_green.filas` antes de subir; si no cuadran, no se sube |
| taxi_zones | cambió el contenido de la tabla (huella SHA-256 en los metadatos) | — |

Para que nadie lea un archivo a medias:
- Las subidas a S3 solo se ven cuando terminan, tanto las multiparte como las de un solo `PUT`.
- El simulador escribe yellow como `.part` y lo renombra al final. La ingesta ignora los `.part`.
- La lectura de MariaDB va en una sola transacción, así que no ve un mes que el simulador esté cargando a medias.
- Solo corre una ingesta a la vez: la Lambda tiene concurrencia reservada en 1 y el script de la EC2 usa `flock`.

Si algo falla, la Lambda termina con error y queda en CloudWatch. No reintenta por su cuenta: el reintento es la corrida siguiente, 5 minutos después. Si la EC2 está apagada, HVFHV se ingiere igual y la parte de la EC2 se omite.

## Archivos

| Archivo | Qué hace |
|---|---|
| [`desplegar.py`](desplegar.py) | Publica el código de la EC2 en `s3://<bucket>/codigo/punto3-ingesta/` y crea o actualiza la Lambda y la regla de EventBridge. Tiene `--pausar` y `--borrar` |
| [`ingestar.py`](ingestar.py) | Invoca la Lambda ya mismo, con el mismo evento que EventBridge, y muestra qué hay en raw. `--estado` solo muestra |
| [`lambda_ingesta.py`](lambda_ingesta.py) | La Lambda `tlc-ingesta` (`LabRole`, Python 3.12, 2 GB, 15 min) |
| [`ec2_ingesta.py`](ec2_ingesta.py) | Lo que corre en la EC2: yellow, green y `taxi_zones`. Usa `fuente.py` del Punto 2 para conectarse a MariaDB |
| [`raw.py`](raw.py) | Rutas de la zona raw |
| [`test_raw.py`](test_raw.py) | Chequeo de las rutas y los rangos de meses: `python punto3-ingesta/test_raw.py` |

## Reproducir

Desde la raíz del repo, con el Punto 2 corriendo (infraestructura, siembra y al menos un mes liberado):

```bash
python punto3-ingesta/desplegar.py          # Lambda + regla de EventBridge (cada 5 min)
python punto3-ingesta/ingestar.py           # primera corrida sin esperar a la regla
```

Para ver la automatización en vivo: liberar un mes y esperar la corrida programada, sin tocar nada más.

```bash
python punto2-fuentes/simular.py --mes 2024-05
# a los ≤ 5 min:
python punto3-ingesta/ingestar.py --estado
```

Al terminar la sesión: `python punto3-ingesta/desplegar.py --pausar` y `python punto2-fuentes/infra/apagar_infra.py`.

## Resultados (2026-11-13)

Primera corrida (manual), con 2024-01 a 2024-03 liberados: 12 archivos en 20 s.

```
HVFHV (URL de la TLC)
  liberados 2024-01 .. 2024-03; faltan en raw: 3
  2024-01: 451 MiB en 7 s
  2024-02: 441 MiB en 5 s
  2024-03: 484 MiB en 7 s
EC2 (yellow, green, taxi_zones): Success
  yellow 2024-01: 2964624 filas, 47.6 MiB -> raw/yellow/year=2024/month=01/yellow_tripdata_2024-01.parquet
  ...
  green 2024-01: 56551 filas, 1.8 MiB -> raw/green/year=2024/month=01/green_tripdata_2024-01.parquet (nuevo)
  ...
Zona raw
  green        3 archivos  2024-01 .. 2024-03   0.01 GiB
  hvfhv        3 archivos  2024-01 .. 2024-03   1.34 GiB
  taxi_zones   1 archivos  sin partición        0.00 GiB
  yellow       3 archivos  2024-01 .. 2024-03   0.15 GiB
```

- **Segunda corrida:** no subió nada ("ya estaban en raw").
- **Corrida automática:** a las 16:24 se liberó 2024-04 (`simular.py --mes 2024-04`) y se recargó green 2024-02 (`--mes 2024-02 --forzar`), sin invocar nada a mano. La corrida programada de EventBridge de las 16:28 dejó los tres archivos de 2024-04 en raw (HVFHV, 454 MiB en 6 s) y reemplazó green 2024-02 con su nuevo `cargado_en`. Yellow 2024-02, que el simulador volvió a bajar idéntico, no se subió de nuevo. Log de esa corrida en CloudWatch (`/aws/lambda/tlc-ingesta`):
  ```
  liberados 2024-01 .. 2024-04; faltan en raw: 1; 2024-04: 454 MiB en 6 s | errores: 0
  yellow 2024-04: 3514289 filas, 56.4 MiB -> raw/yellow/year=2024/month=04/yellow_tripdata_2024-04.parquet
  green 2024-02: 53577 filas, 1.7 MiB -> raw/green/year=2024/month=02/green_tripdata_2024-02.parquet (reemplazado)
  green 2024-04: 56471 filas, 1.8 MiB -> raw/green/year=2024/month=04/green_tripdata_2024-04.parquet (nuevo)
  ```
- **Green de 2024-01 contra el archivo original de la TLC:** las mismas 56.551 filas, la misma suma de `total_amount` (1.266.922,59) y de `tip_amount`, y el mismo pickup mínimo.

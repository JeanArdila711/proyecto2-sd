# Punto 2 — Fuentes de datos

La rúbrica pide simular datos en tres tipos de fuente. Repartimos los datos de la TLC así:

| Fuente | Qué contiene | Volumen |
|---|---|---|
| **RDS MariaDB** (`tlc-mariadb`) | Tablas `taxi_zones` (265 zonas) y `green_trips` (taxis verdes 2024–2025) | 265 filas + ~1,3 M filas |
| **Archivos en EC2** (`tlc-fuente-archivos`) | Los 24 Parquet mensuales de taxis amarillos 2024–2025 en `/data/tlc/yellow` | 1,42 GiB |
| **URL en Internet** | Los 48 Parquet mensuales de Uber y Lyft (HVFHV) en `https://d37ci6vzurychx.cloudfront.net/trip-data/` | 10,93 GiB |

Por qué este reparto: la tabla de zonas en la base de datos la usan las seis preguntas; cada fuente tiene el volumen que le corresponde (transaccional, servidor de archivos, portal de datos abiertos); y cada una se ingiere con una técnica distinta en el Punto 3.

## Infraestructura

[`infra/crear_infra.py`](infra/crear_infra.py) crea todo con boto3. Es idempotente: si algo ya existe lo reutiliza, y si la EC2 o la RDS están detenidas (pasa al reiniciar el laboratorio) las arranca.

| Recurso | Nombre | Detalle |
|---|---|---|
| Bucket del datalake | `proyecto2-tlc-<sufijo>` | Privado. El sufijo sale de un hash de la cuenta, así que es estable y no expone el ID |
| Security group EC2 | `tlc-ec2-sg` | SSH (22) solo desde tu IP pública |
| Security group RDS | `tlc-rds-sg` | 3306 desde `tlc-ec2-sg`; TCP desde sí mismo para la conexión JDBC de Glue (Punto 3) |
| Endpoint gateway de S3 | `tlc-s3-endpoint` | Para que Glue, dentro de la VPC, llegue a S3 |
| RDS MariaDB | `tlc-mariadb` | MariaDB 11.8 (LTS), `db.t3.micro`, 20 GB gp3, privada, base `tlc`, usuario `tlcadmin` |
| EC2 | `tlc-fuente-archivos` | `t3.small`, Amazon Linux 2023, `LabInstanceProfile`, llave `vockey`, 20 GB; trae Python 3.11 y el cliente de MariaDB |
| Parámetro `/proyecto2-sd/db/password` | Parameter Store, `SecureString` | Contraseña de MariaDB, copiada de `config.env`; la leen la EC2 y luego Glue |

AWS Academy no deja crear roles IAM: la EC2 usa `LabInstanceProfile` y los demás servicios usarán `LabRole`.

### Reproducir

Desde la raíz del repo, con el entorno y `config.env` listos (ver el README principal):

```bash
python punto2-fuentes/infra/crear_infra.py
```

Si `DB_PASSWORD` está vacía en `config.env`, el script genera una y la guarda ahí. Al final imprime el bucket, la IP de la EC2 y el endpoint de la RDS. Tarda unos 10 minutos por la RDS.

Para entrar a la EC2: descarga `labsuser.pem` desde *AWS Details* en el Learner Lab y corre `ssh -i labsuser.pem ec2-user@<IP>`. También funciona Session Manager desde la consola.

Para apagar o borrar al terminar:

```bash
python punto2-fuentes/infra/apagar_infra.py                                # detiene EC2 y RDS; conserva los datos
python punto2-fuentes/infra/destruir_infra.py --confirmar                  # borra todo menos el bucket
python punto2-fuentes/infra/destruir_infra.py --confirmar --incluir-bucket
```

`crear_infra.py` vuelve a encender lo que esté detenido. AWS enciende sola una RDS detenida a los 7 días.

## Siembra

```bash
python punto2-fuentes/sembrar.py
```

Crea el esquema de MariaDB ([`ec2/esquema.sql`](ec2/esquema.sql)), carga las 265 zonas desde el CSV de la TLC y prepara `/data/tlc/yellow`. Es idempotente.

Como la RDS es privada, todo lo que habla con MariaDB corre **dentro de la EC2**. [`remoto.py`](remoto.py) sube `ec2/` a `s3://<bucket>/codigo/punto2-fuentes/ec2/` y lo ejecuta en la EC2 por Session Manager (sin SSH), en un entorno de Python 3.11 en `/opt/proyecto2/venv`. La contraseña se lee de Parameter Store; nunca viaja en el comando.

Tablas en la base `tlc`:

| Tabla | Contenido |
|---|---|
| `taxi_zones` | Las 265 zonas; llave primaria `LocationID` |
| `green_trips` | Columnas del archivo de la TLC + auditoría: `trip_id` (autoincremental), `mes_archivo` (mes del archivo de origen) y `cargado_en`. `PULocationID` y `DOLocationID` son llaves foráneas a `taxi_zones` |
| `cargas_green` | Qué meses cargó el simulador y cuántas filas |

## Simulador de llegada de datos

Los datos de 2024 y 2025 ya están publicados completos. Para mostrar la ingesta automática, el simulador libera meses en las tres fuentes como si llegaran mes a mes:

```bash
python punto2-fuentes/simular.py --mes 2024-01
python punto2-fuentes/simular.py --desde 2024-02 --hasta 2024-06
python punto2-fuentes/simular.py --estado            # qué hay en cada fuente, sin cambiar nada
python punto2-fuentes/simular.py --mes 2024-01 --forzar
```

Por cada mes:

| Fuente | Qué hace |
|---|---|
| RDS MariaDB | Descarga el Parquet de green del mes y lo inserta en `green_trips` (lotes de 5.000 filas) |
| Archivos en EC2 | Descarga `yellow_tripdata_<mes>.parquet` a `/data/tlc/yellow` (escribe a `.part` y renombra, para que la ingesta nunca vea un archivo a medias) |
| URL | Adelanta el **reloj simulado** `/proyecto2-sd/simulacion/mes_actual` (Parameter Store). La ingesta de HVFHV descarga de la TLC solo hasta ese mes |

Repetir un mes no duplica nada: sin `--forzar` lo salta; con `--forzar` borra las filas de ese mes y las vuelve a cargar. Cada mes tarda unos 4 segundos.

Resultado de la primera prueba (2026-11-11):

```
Estado de las fuentes
  RDS   taxi_zones: 265 filas | green_trips: 167585 filas, 3 meses (2024-01 .. 2024-03)
  EC2   /data/tlc/yellow: 3 archivos yellow, 0.15 GiB (2024-01 .. 2024-03)
  URL   reloj simulado: 2024-03
```

Las filas de green coinciden con el archivo de la TLC (56.551 en 2024-01).

## Pendiente

- Evidencias (capturas de la consola de RDS, la EC2 y Parameter Store).

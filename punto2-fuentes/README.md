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
| EC2 | `tlc-fuente-archivos` | `t3.small`, Amazon Linux 2023, `LabInstanceProfile`, llave `vockey`, 20 GB; trae `python3-pip` y el cliente de MariaDB |

AWS Academy no deja crear roles IAM: la EC2 usa `LabInstanceProfile` y los demás servicios usarán `LabRole`.

### Reproducir

Desde la raíz del repo, con el entorno y `config.env` listos (ver el README principal):

```bash
python punto2-fuentes/infra/crear_infra.py
```

Si `DB_PASSWORD` está vacía en `config.env`, el script genera una y la guarda ahí. Al final imprime el bucket, la IP de la EC2 y el endpoint de la RDS. Tarda unos 10 minutos por la RDS.

Para entrar a la EC2: descarga `labsuser.pem` desde *AWS Details* en el Learner Lab y corre `ssh -i labsuser.pem ec2-user@<IP>`. También funciona Session Manager desde la consola.

Para borrar todo al terminar:

```bash
python punto2-fuentes/infra/destruir_infra.py --confirmar                  # deja el bucket
python punto2-fuentes/infra/destruir_infra.py --confirmar --incluir-bucket
```

## Pendiente

- Siembra: crear el esquema en MariaDB y cargar `taxi_zones`.
- Simulador: liberar un mes a la vez en las tres fuentes.
- Evidencias (capturas de la consola).

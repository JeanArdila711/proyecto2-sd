# punto2-fuentes — Context

**Tracker:** none
**Status:** In progress · **Owner:** David

## Orientation

Construir las tres fuentes simuladas del Punto 2 según la convención "Fuentes de datos" (`planificacion/current/fuentes-de-datos.md`): la infraestructura en AWS Academy, la siembra de MariaDB y la EC2, y el simulador que libera un mes a la vez. El código vive en `punto2-fuentes/` en la raíz del repo. El topic se cierra cuando las tres fuentes tienen datos, el simulador funciona y el Punto 2 del Docx tiene evidencias.

## Rulings

- **Recursos del Punto 2 (David, 2026-11-11 20:30):** MariaDB 11.8 (rama LTS, último parche) en `db.t3.micro` con 20 GB gp3, privada, sin backups ni Multi-AZ; EC2 `t3.small` con Amazon Linux 2023 y 20 GB. Tamaños mínimos que alcanzan para ~1,3 M filas y 1,42 GiB.
- **Código en la EC2 por SSM (David, 2026-11-11 21:30):** lo que corre en la EC2 vive en `punto2-fuentes/ec2/`; `remoto.py` lo publica en `s3://<bucket>/codigo/` y lo ejecuta por Session Manager en `/opt/proyecto2/venv` (Python 3.11). La contraseña se lee de `/proyecto2-sd/db/password`, nunca va en el comando.
- **RDS privada; la siembra corre desde la EC2 (David, 2026-11-11 20:30):** la RDS no es pública. Solo entra el puerto 3306 desde `tlc-ec2-sg` y TCP desde `tlc-rds-sg` (Glue JDBC). Todo lo que hable con MariaDB corre en la EC2 o dentro de la VPC, no desde el portátil.

_Every ruling passes the scope test when it is written (skill `memoria-equipo` § Decisiones). Put a date in the bold label: the checker reads it._

## Journal (newest first)

**2026-11-11, evidencias (David):** Punto 2 del Docx reescrito con lo implementado (infraestructura, esquema con auditoría, siembra y simulador por SSM, comandos para reproducir) y 6 figuras: consola de RDS, EC2 y Parameter Store (ID de cuenta y usuario enmascarados, verificado), salida del simulador, consulta a MariaDB con JOIN por borough y archivos de yellow. Extractos de `esquema.sql` y `simulador.py`. Infraestructura apagada con `apagar_infra.py` al cerrar. Pendiente para cerrar el topic: probar `destruir_infra.py` (al final del proyecto).

**2026-11-11, siembra y simulador (David):** `sembrar.py` y `simular.py` corren el código de `ec2/` dentro de la EC2 por SSM (`remoto.py`), con un venv de Python 3.11. Esquema aplicado (`taxi_zones`, `green_trips` con columnas de auditoría, `cargas_green`), 265 zonas cargadas. Simulador probado: 2024-01 a 2024-03 liberados (167.585 filas de green, 3 archivos de yellow, reloj en 2024-03); repetir un mes no duplica, `--forzar` recarga con el mismo total, y las filas cuadran con el Parquet de la TLC. Contraseña en Parameter Store. Nuevo `infra/apagar_infra.py`. Falla corregida: el esquema se partía por `;` dentro de comentarios. Pendiente: evidencias del Docx; `destruir_infra.py` sin probar.

**2026-11-11 (David):** Esqueleto del repo (un directorio por punto, `comun/config.py`, `config.example.env`, `.gitignore`) y `infra/crear_infra.py` / `destruir_infra.py` con boto3. Infraestructura creada y verificada: bucket `proyecto2-tlc-<sufijo>`, `tlc-mariadb` (MariaDB 11.8.9) disponible, EC2 `tlc-fuente-archivos` con cloud-init terminado, cliente MariaDB 10.5, carpeta `/data/tlc/yellow`, acceso a S3 por `LabInstanceProfile` y el puerto 3306 alcanzable desde la EC2 (comprobado por SSM). Segunda corrida del script: todo "ya existe". Pendiente: siembra y simulador.

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| — | — | — | Sin documentos propios todavía; el diseño está en `planificacion/current/fuentes-de-datos.md` y el código en `punto2-fuentes/` |

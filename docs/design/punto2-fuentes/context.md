# punto2-fuentes — Context

**Tracker:** none
**Status:** In progress · **Owner:** David

## Orientation

Construir las tres fuentes simuladas del Punto 2 según la convención "Fuentes de datos" (`planificacion/current/fuentes-de-datos.md`): la infraestructura en AWS Academy, la siembra de MariaDB y la EC2, y el simulador que libera un mes a la vez. El código vive en `punto2-fuentes/` en la raíz del repo. El topic se cierra cuando las tres fuentes tienen datos, el simulador funciona y el Punto 2 del Docx tiene evidencias.

## Rulings

- **Recursos del Punto 2 (David, 2026-11-11 20:30):** MariaDB 11.8 (rama LTS, último parche) en `db.t3.micro` con 20 GB gp3, privada, sin backups ni Multi-AZ; EC2 `t3.small` con Amazon Linux 2023 y 20 GB. Tamaños mínimos que alcanzan para ~1,3 M filas y 1,42 GiB.
- **RDS privada; la siembra corre desde la EC2 (David, 2026-11-11 20:30):** la RDS no es pública. Solo entra el puerto 3306 desde `tlc-ec2-sg` y TCP desde `tlc-rds-sg` (Glue JDBC). Todo lo que hable con MariaDB corre en la EC2 o dentro de la VPC, no desde el portátil.

_Every ruling passes the scope test when it is written (skill `memoria-equipo` § Decisiones). Put a date in the bold label: the checker reads it._

## Journal (newest first)

**2026-11-11 (David):** Esqueleto del repo (un directorio por punto, `comun/config.py`, `config.example.env`, `.gitignore`) y `infra/crear_infra.py` / `destruir_infra.py` con boto3. Infraestructura creada y verificada: bucket `proyecto2-tlc-<sufijo>`, `tlc-mariadb` (MariaDB 11.8.9) disponible, EC2 `tlc-fuente-archivos` con cloud-init terminado, cliente MariaDB 10.5, carpeta `/data/tlc/yellow`, acceso a S3 por `LabInstanceProfile` y el puerto 3306 alcanzable desde la EC2 (comprobado por SSM). Segunda corrida del script: todo "ya existe". La EC2 trae Python 3.9: los scripts que corran ahí no usan sintaxis de 3.10+. Pendiente: siembra y simulador; `destruir_infra.py` no se ha probado.

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| — | — | — | Sin documentos propios todavía; el diseño está en `planificacion/current/fuentes-de-datos.md` y el código en `punto2-fuentes/` |

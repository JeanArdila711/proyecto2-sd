# punto3-ingesta — Context

**Tracker:** none
**Status:** In progress · **Owner:** Jean

## Orientation

Implementar la ingesta automática del Punto 3 según las convenciones "Ingesta automática" y "Layout de la zona raw" (`CONTEXT.md`): Lambda `tlc-ingesta` para HVFHV, `ec2_ingesta.py` por SSM para yellow, green y `taxi_zones`, y la regla de EventBridge que dispara las dos. El código vive en `punto3-ingesta/` en la raíz del repo, y su README tiene el diseño y los resultados. El topic se cierra cuando la ingesta corre sola en AWS, el README tiene evidencias y el Punto 3 del Docx está lleno.

## Rulings

- **Green por partición mensual, no por `trip_id` (Jean, 2026-11-13 16:30):** green se extrae un mes completo por vez (`mes_archivo`) y reemplaza su archivo cuando cambia `cargas_green.cargado_en`. `trip_id` queda en el Parquet como auditoría, no como watermark: cubre las recargas con `--forzar`, que un watermark no ve.
- **Tipos de green desde el esquema de MariaDB (Jean, 2026-11-13 16:30):** el Parquet toma los tipos de `cursor.description`, no los infiere de los valores, para que los meses con columnas todas en NULL (`cbd_congestion_fee` en 2024) compartan esquema con 2025.
- **Una corrida a la vez y sin reintentos propios (Jean, 2026-11-13 16:30):** la Lambda tiene concurrencia reservada en 1 y `MaximumRetryAttempts=0`. La EC2 usa `flock`. El reintento es la corrida siguiente de EventBridge.

_Every ruling passes the scope test when it is written (skill `memoria-equipo` § Decisiones). Put a date in the bold label: the checker reads it._

## Journal (newest first)

**2026-11-13, carga completa (Jean):** Liberados 2024-05 a 2025-11 e ingeridos en una invocación de 2 min 9 s. Raw con 23 meses por dataset (HVFHV 10,43 GiB, yellow 1,35 GiB, green 0,04 GiB). Green cuadra con MariaDB (1.203.357 filas) y el `cbd_congestion_fee` de 2025-06 con la TLC. 2025-12 se guarda para la demo.

**2026-11-13 (Jean):** Implementada y desplegada en la cuenta de Jean: `raw.py`, `lambda_ingesta.py`, `ec2_ingesta.py`, `desplegar.py`, `ingestar.py`, `test_raw.py` y README. Primera corrida: 12 archivos en raw en 20 s (HVFHV a ~65–90 MB/s). La segunda no subió nada. Green de 2024-01 cuadra contra el archivo de la TLC (filas, sumas, fechas). Academy permite Lambda → SSM `SendCommand`, `put_function_concurrency` y la regla de EventBridge con `add_permission`. En la revisión propia se corrigieron excepciones sin capturar (`S3UploadFailedError`, descargas cortadas). Pendiente: evidencias del Docx.

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| — | — | — | Sin documentos propios; el diseño y los resultados están en `punto3-ingesta/README.md` |

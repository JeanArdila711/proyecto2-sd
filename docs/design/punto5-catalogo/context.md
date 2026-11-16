# punto5-catalogo — Context

**Tracker:** none
**Status:** In progress · **Owner:** David

## Orientation

Punto 5 de la rúbrica: tablas SQL sobre `trusted/` en el Glue Data Catalog y en EMR/Hive. David lo desarrolla en su cuenta de Academy, sobre una muestra de 3 meses (2024-01 a 2024-03) generada con los Puntos 3 y 4, y Jean corre los mismos scripts al final en la cuenta de la demo (convención "Cuenta de la demo"). El encargo completo, con el orden, las reglas y la verificación, está en `current/encargo.md`. El topic se cierra cuando los scripts de `punto5-catalogo/` crean las tablas en las dos cuentas, los conteos de Athena y Hive coinciden con los controles y el README del punto tiene evidencias.

## Rulings

- **Cómo se cataloga (Jean, 2026-11-16 13:00):** Verdict: per project CONTEXT Conventions ("Catalogación"). Topic detail: los nombres de la base de datos y del workgroup, y la integración del paso en la state machine, quedan en manos de David, con revisión de Jean.

_Every ruling passes the scope test when it is written (skill `memoria-equipo` § Decisiones). Put a date in the bold label: the checker reads it._

## Journal (newest first)

**2026-11-16 (Jean):** Topic abierto para David con el encargo en `current/encargo.md`: muestra de trusted en su cuenta (fase A) y catalogación (fase B). Trusted de la cuenta de Jean se está recargando con `viajes`. Siguiente: David arranca por la fase A.

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| `current/encargo.md` | reference | always | Qué hacer y en qué orden: muestra en la cuenta de David, Punto 5, reglas de Glue y EMR, verificación y entrega |

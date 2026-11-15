# punto4-trusted — Context

**Tracker:** none
**Status:** In progress · **Owner:** Jean

## Orientation

Punto 4 de la rúbrica: preparación de datos de `raw/` a `trusted/` con AWS Glue y Apache Spark, automática y encadenable con la ingesta (convención "Ingesta automática"). Parte de los 24 meses en raw de la cuenta de Jean (convención "Cuenta de la demo"). Se diseña con RePPIT: las etapas viven en `working/`. La normalización de tarifas depende de P2 y P3 (README § Open decisions), que siguen abiertas. El topic se cierra cuando trusted se genera solo en AWS, el README del punto tiene evidencias y el Punto 4 del Docx está lleno.

## Rulings

_Every ruling passes the scope test when it is written (skill `memoria-equipo` § Decisiones). Put a date in the bold label: the checker reads it._

## Journal (newest first)

**2026-11-15 (Jean):** Topic abierto. Research de RePPIT escrito en `working/research.md` (esquemas reales de raw leídos de los footers, requisitos, calidad, patrones y Glue en Academy). Falta que Jean lo revise antes de la propuesta.

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| `working/research.md` | draft | on-demand | Research de RePPIT: raw tal como está, requisitos, calidad, patrones del repo y Glue en Academy |

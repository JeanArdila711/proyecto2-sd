# punto4-trusted — Context

**Tracker:** none
**Status:** In progress · **Owner:** Jean

## Orientation

Punto 4 de la rúbrica: preparación de datos de `raw/` a `trusted/` con AWS Glue y Apache Spark, automática y encadenable con la ingesta (convención "Ingesta automática"). Parte de los 24 meses en raw de la cuenta de Jean (convención "Cuenta de la demo"). Se diseña con RePPIT: las etapas viven en `working/`. La normalización de tarifas depende de P2 y P3 (README § Open decisions), que siguen abiertas. El topic se cierra cuando trusted se genera solo en AWS, el README del punto tiene evidencias y el Punto 4 del Docx está lleno.

## Rulings

- **Diseño de trusted (Jean, 2026-11-15 19:30):** Verdict: per project CONTEXT Conventions ("Layout de la zona trusted"). Topic detail: un solo Glue job escribe las dos salidas por (dataset, mes). Una state machine lanza solo lo que cambió y la dispara la Lambda de ingesta (plan B: `preparar_local.py`). Se construye primero el detalle y después `viajes`. Discussion: `working/proposal.md` § Dirección elegida.

_Every ruling passes the scope test when it is written (skill `memoria-equipo` § Decisiones). Put a date in the bold label: the checker reads it._

## Journal (newest first)

**2026-11-16, implement, sesión 2 (Jean):** Verificaciones manuales de las fases 2 a 4 hechas con evidencia: `--forzar` y encadenamiento solo tocan su mes, y la segunda invocación no arranca otra ejecución. Fase 5 implementada (contrato, job y `--estado`), revisada por el `revisor` y probada en green 2024-01: raw = detalle = viajes. Recarga de los 72 meses con `viajes` lanzada (~4 h). Detalle en `working/plan.md` § Notas de implementación. Siguiente: `--estado`, fase 6 y review.

**2026-11-16, implement (Jean):** Fases 0, 1 y 4 hechas y la 2 desplegada. La cuenta del primer curso se desactivó por correr tres jobs de Glue a la vez, y se replicó todo en la cuenta del segundo curso. La capa de detalle de trusted está completa: 73 controles, raw = detalle, idempotente. Todo con un job a la vez y 2 workers, hasta conocer los límites de Glue de Vocareum. El estado fino está en `working/plan.md` § Notas de implementación. Siguiente: dos verificaciones cortas y la fase 5 (`viajes`).

**2026-11-15, plan (Jean):** Plan de RePPIT en `working/plan.md`: fase 0 de permisos de `LabRole`, detalle, state machine con control en `trusted/_control/`, encadenamiento, carga completa, `viajes` y README. Verificados en docs oficiales los vacíos del research (vistas de Athena, overwrite, workers y precio, zonas 264/265). Siguiente: `/reppit-implement punto4-trusted`.

**2026-11-15, propuesta (Jean):** Dos propuestas y una combinación en `working/proposal.md`. Jean eligió la combinación con dos ajustes (ruling "Diseño de trusted"). Siguiente: plan.

**2026-11-15 (Jean):** Topic abierto. Research de RePPIT escrito en `working/research.md` (esquemas reales de raw leídos de los footers, requisitos, calidad, patrones y Glue en Academy). Falta que Jean lo revise antes de la propuesta.

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| `working/plan.md` | draft | always | Plan de RePPIT del Punto 4 con checkboxes y Notas de implementación (estado de la ejecución) |
| `working/proposal.md` | draft | on-demand | Dos propuestas de RePPIT: tres tablas con banderas frente a tabla unificada con cuarentena |
| `working/research.md` | draft | on-demand | Research de RePPIT: raw tal como está, requisitos, calidad, patrones del repo y Glue en Academy |

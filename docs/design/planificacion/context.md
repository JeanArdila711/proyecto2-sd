# planificacion — Context

**Tracker:** none
**Status:** In progress · **Owner:** Jean

## Orientation

Dejar planificado el Proyecto 2 antes de construir nada: caso de estudio, preguntas de negocio, fuentes de datos (RDS MariaDB, EC2 y URL), arquitectura del pipeline nuevo en AWS Academy y reparto del trabajo en topics que puedan ejecutar agentes. Punto 2 (fuentes) decidido el 2026-11-11. El topic se cierra cuando cada uno de los 8 puntos de la rúbrica tiene un topic o una fase con su plan.

## Rulings

- **Preguntas escogidas (Jean, 2026-11-10 17:00):** las seis de `current/preguntas-de-negocio.md` (P1–P6). P6 la propuso Claude y Jean la confirmó.
- **Planificar antes de construir (Jean, 2026-11-10 17:00):** no se diseña ni se toca el pipeline hasta cerrar la planificación.

_Every ruling passes the scope test when it is written (skill de memoria § Decisiones). Put a date in the bold label: the checker reads it._

## Journal (newest first)

**2026-11-11 (David):** Se diligenció el Docx del enunciado: integrantes, link del repo, Punto 1 (caso de estudio, datos, P1–P6, consideraciones de calidad) y Punto 2. Conexión a AWS Academy por CLI y verificación de límites por servicio (findings). Decidido el reparto de fuentes: RDS = `taxi_zones` + green, EC2 = yellow, URL = HVFHV, más un simulador de llegada mensual (`current/fuentes-de-datos.md`). Pendiente: extracción RDS → S3 (Glue JDBC o script en EC2), P2/P3, arquitectura y topics.

**2026-11-10:** Arranque del proyecto. Se resumió la rúbrica, se analizó el proyecto TLC del curso como referencia (informe en `evidence/`), se revisaron la guía de usuario, la página de datos y los diccionarios de la TLC, se fijó el alcance de datos (2024–2025, yellow + green + HVFHV) y se escogieron las seis preguntas, verificadas contra los parquets leyendo footers y row groups de muestra. Se montó esta memoria, con una versión de equipo de la skill (`.claude/skills/memoria-equipo/`) y `AGENTS.md` para los otros integrantes. Jean sigue con su `memoria-proyecto` global. Obsidian quedó como notas del equipo para entender el proyecto. Nada commiteado: Jean sube el repo cuando lo decida. Cierre: `design_check.py` → 0 FAIL, 0 WARN; lecturas manuales OK. Pendiente: fuentes MariaDB/EC2, definiciones de P2 y P3, arquitectura y topics.

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| `current/rubrica.md` | reference | always | Los 8 puntos de la rúbrica, herramientas exigidas y entregables |
| `current/preguntas-de-negocio.md` | deliverable | always | P1–P6, campos que usa cada una, puntos abiertos e inventario de datos con volúmenes |
| `current/fuentes-de-datos.md` | deliverable | always | Punto 2: qué datos van en RDS, EC2 y URL, por qué, siembra, simulador y puntos abiertos |
| `evidence/informe-proyecto-base-tlc.md` | reference | on-demand | Informe del subagente sobre el pipeline TLC del curso: arquitectura, recursos, lecciones (ID de cuenta redactado) |

# Proyecto 2 Big Data TLC Changelog

Newest first. One `##` heading per day with activity. Write outcomes, not implementation steps. This file is appended to, never rewritten, and is not loaded by default.

## 2026-11-10

### planificacion — arranque del proyecto y memoria
- Se resumió la rúbrica de SI3007 (8 puntos, entrega y sustentación el 2026-11-19).
- Se analizó el pipeline TLC del curso Fundamentos Data Engineering. Queda como referencia de patrones; el pipeline de este proyecto se diseña de cero.
- Decidido: AWS Academy como cuenta; alcance de datos yellow + green + HVFHV + zonas, 2024–2025 (72 archivos, 12,38 GiB).
- Escogidas seis preguntas de negocio (P1–P6), verificadas contra los parquets leyendo footers y row groups de muestra.
- Se montó la memoria del proyecto en `docs/design/`.

### equipo — protocolo de memoria compartido
- Versión general de la skill de memoria en el repo (`memoria-equipo`), para que los agentes de los otros integrantes sigan el mismo protocolo: sin Obsidian, sin hooks ni rutas locales, con reglas de equipo (una persona a la vez, `git pull` al empezar, commit + push al cerrar).
- `AGENTS.md` para agentes que no leen `CLAUDE.md`.
- Ajuste: `memoria-equipo` es solo para los otros integrantes; Jean sigue con su `memoria-proyecto` global. Obsidian queda como las notas del equipo para entender el proyecto, no como memoria de agentes.

### Files (proyecto2-sd, branch main)
- `CLAUDE.md`, `AGENTS.md` (new)
- `.claude/skills/memoria-equipo/` (new: `SKILL.md`, `templates/`, `references/`, `scripts/design_check.py`)
- `docs/design/CONTEXT.md`, `README.md`, `CHANGELOG.md`, `findings.md`, `INDEX.md` (new)
- `docs/design/planificacion/context.md`, `current/rubrica.md`, `current/preguntas-de-negocio.md`, `evidence/informe-proyecto-base-tlc.md` (new)

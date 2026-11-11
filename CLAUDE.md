# proyecto2-sd

@docs/design/CONTEXT.md

- La memoria del proyecto vive en `docs/design/`. Jean la maneja con su skill global `memoria-proyecto`; los demás integrantes, con la skill del repo `memoria-equipo` (`.claude/skills/memoria-equipo/SKILL.md`). Las dos comparten layout, formato y checker.
- **Al empezar:** `git pull`, leer `docs/design/CONTEXT.md` y el `context.md` del topic activo, y resumir en 3–4 líneas dónde quedó el proyecto.
- **Al terminar:** cierre de sesión de la skill (CHANGELOG, Active Context, journal y document map), `python3 .claude/skills/memoria-equipo/scripts/design_check.py docs/design` sin FAIL, y commit + push.
- El repo es público: no se commitean credenciales, IDs de cuenta AWS ni `.env`.

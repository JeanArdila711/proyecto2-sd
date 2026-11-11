# proyecto2-sd — instrucciones para agentes

Para agentes que no leen `CLAUDE.md` (Codex, Cursor, Copilot, etc.).

1. Antes de hacer cualquier cosa, leer `.claude/skills/memoria-equipo/SKILL.md` y seguirlo: es el protocolo de memoria del proyecto.
2. **Al empezar:** `git pull`, leer `docs/design/CONTEXT.md` y el `context.md` del topic activo, y resumir en 3–4 líneas dónde quedó el proyecto.
3. **Al terminar:** cierre de sesión del protocolo (CHANGELOG, Active Context, journal y document map), `python3 .claude/skills/memoria-equipo/scripts/design_check.py docs/design` sin FAIL, y commit + push.
4. El repo es público: no se commitean credenciales, IDs de cuenta AWS ni `.env`.

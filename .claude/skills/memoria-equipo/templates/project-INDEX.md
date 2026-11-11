# {Project name} — Índice de informes

Informes de subagentes que vale la pena reusar. Se lee antes de explorar o delegar. Una fila por tema; al actualizar un informe se reemplaza su fila.

Vigencia: `git diff --stat <commit> -- <cubre>`. Vacío → vigente, se usa tal cual. Con cambios → se parte del informe y se relee solo lo que cambió.

| Fecha | Tema | Commit | Cubre | Informe |
|---|---|---|---|---|
| {YYYY-MM-DD} | {tema} | {git rev-parse --short HEAD} | {rutas que leyó} | {ruta del informe} |

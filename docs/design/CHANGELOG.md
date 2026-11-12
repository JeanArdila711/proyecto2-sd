# Proyecto 2 Big Data TLC Changelog

Newest first. One `##` heading per day with activity. Write outcomes, not implementation steps. This file is appended to, never rewritten, and is not loaded by default.

## 2026-11-11

### planificacion — Docx, límites de AWS y fuentes (David)
- Docx del enunciado diligenciado: integrantes, link del repo (`JeanArdila711/proyecto2-sd`), Punto 1 y Punto 2. El Docx quedó versionado en la raíz del repo (commit `e9056cd`).
- Límites de AWS Academy verificados por CLI sin dejar recursos: regiones, tamaños de EC2 y RDS, Lambda, Glue, EMR; no se pueden crear roles IAM (2 findings).
- Decidido el reparto de fuentes del Punto 2 (convención "Fuentes de datos"): se descartaron solo zonas en RDS (base de datos decorativa) y yellow en RDS (~90 M filas para `db.t3.micro`). Se agregó un simulador de llegada mensual para demostrar la ingesta automática.
- Convención nueva "Roles de AWS Academy".

### punto2-fuentes — esqueleto del repo e infraestructura (David)
- Topic nuevo `punto2-fuentes`. Repo con un directorio por punto de la rúbrica, README principal con los pasos para reproducir y `comun/config.py` con los nombres de los recursos.
- Infraestructura del Punto 2 creada en AWS Academy con `punto2-fuentes/infra/crear_infra.py` (boto3, idempotente): bucket del datalake, RDS MariaDB 11.8, EC2 de archivos, security groups y endpoint de S3. Verificada desde la EC2 por SSM.
- Siembra y simulador funcionando: esquema de MariaDB y 265 zonas cargadas; liberados 2024-01 a 2024-03 en las tres fuentes (167.585 filas de green que cuadran con la TLC, 3 Parquet de yellow, reloj simulado en 2024-03). El código de la EC2 se ejecuta por SSM con Python 3.11; contraseña en Parameter Store. Nuevo `apagar_infra.py`.
- Punto 2 del Docx con evidencias: 3 capturas de la consola (ID de cuenta enmascarado) y 3 de terminal, más extractos de código. Hallazgos: MariaDB 11.8 en RDS exige TLS; cómo enmascarar capturas de la consola. EC2 y RDS apagadas al cerrar.
- La convención "Fuentes de datos" ahora incluye el contrato con la ingesta (reloj simulado, columnas de auditoría, escritura atómica).
- Convención nueva "Infraestructura por scripts". Se terminaron las 3 instancias `dfsha-nodo-*` de otro trabajo que gastaban presupuesto del laboratorio.

### Files (proyecto2-sd, branch main)
- `docs/design/planificacion/current/fuentes-de-datos.md` (new)
- `README.md`, `.gitignore`, `config.example.env`, `requirements.txt`, `comun/`, `punto1-caso-de-estudio/` … `punto8-visualizacion-app/` (new)
- `docs/design/punto2-fuentes/context.md` (new)
- `punto2-fuentes/sembrar.py`, `simular.py`, `remoto.py`, `ec2/` (`esquema.sql`, `fuente.py`, `sembrar.py`, `simulador.py`, `requirements.txt`), `infra/apagar_infra.py` (new)
- `docs/design/CONTEXT.md`, `README.md`, `CHANGELOG.md`, `findings.md`, `planificacion/context.md`, `planificacion/current/rubrica.md`
- `SI3007-262-proyecto2.docx`

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

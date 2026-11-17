# Proyecto 2 Big Data TLC Changelog

Newest first. One `##` heading per day with activity. Write outcomes, not implementation steps. This file is appended to, never rewritten, and is not loaded by default.

## 2026-11-16

### punto5-catalogo — catálogo, Athena y Hive (Jean)
- El Punto 5 pasa a Jean; los Puntos 6–8 los hace un compañero. El encargo de David queda archivado.
- `punto5-catalogo/`: `catalogo.py` (también Lambda `tlc-catalogo`), `desplegar.py`, `verificar.py` y `emr_hive.py` + `hive.q`. La state machine del Punto 4 suma el paso `Catalogar`.
- En la cuenta de la demo: base `tlc_trusted` con 5 tablas y 144 particiones. Athena coincide con los controles en todas las particiones, y Hive en un EMR de un nodo leyó el mismo catálogo; el cluster se apagó solo en 778 s.
- Verificado de paso: `cbd_fee` es NULL en 2024 y tiene valores en 2025. Un finding nuevo sobre EMR en Academy.

### punto4-trusted — verificaciones y `viajes` (Jean)
- Verificadas en AWS las fases 2 a 4: un `--forzar` toca solo su mes, la ingesta dispara la preparación y no arranca una segunda ejecución si ya hay una en curso. Costo acumulado de Glue en la cuenta nueva: ~6 DPU-hora (~USD 2,64).
- Fase 5: `trusted/viajes` en el contrato y el job, probada en green 2024-01 (raw = detalle = viajes). Recarga de los 72 meses lanzada.
- Recarga completa terminada a las 17:25 (~4 h 41 min, ~7,3 DPU-hora, ~USD 3,2): 73 controles con raw = detalle = viajes. Yellow tiene 89,9 M filas, green 1,25 M y HVFHV 483 M.
- Obsidian: la nota "Proyecto 2 - Dinámica del pipeline" explica el Punto 4 para la sustentación (job, dos salidas, banderas, columnas descartadas, workers y jobs de Glue). El hub del proyecto quedó al día.
- Dos findings: marcadores `_$folder$` de Glue en trusted, y la EC2 encendida al iniciar el lab.
- Como el profesor no responde, Glue queda en 2 workers y un job a la vez.

### punto5-catalogo — cómo se cataloga (Jean)
- Convención "Catalogación": DDL desde el contrato, particiones desde los controles y un paso en la state machine. Se descartaron el crawler y la partition projection.

### planificacion — P2 y P3 cerradas (Jean)
- P2: tarifa base más recargos por milla. P3: (`driver_pay` + propina) sobre todo lo que paga el pasajero. Ver Conventions.

### punto5-catalogo — topic abierto (Jean para David)
- Encargo para David: muestra de 3 meses de trusted en su cuenta y catalogación. Sus scripts se corren al final en la cuenta de la demo.

### punto4-trusted — implementación, capa de detalle (Jean)
- Plan de RePPIT aprobado y escrito; código del Punto 4 en `punto4-preparacion/`: contrato, Glue job, Lambda de pendientes, state machine `tlc-preparacion` y encadenamiento desde `tlc-ingesta`.
- `LabRole` permite Glue 5.0 y Step Functions con `glue:startJobRun.sync`, también `StartExecution` desde la Lambda; no hace falta plan B (finding nuevo).
- La cuenta de Academy del primer curso de Jean quedó desactivada al correr tres jobs de Glue a la vez (finding nuevo). Revertida la convención "Cuenta de la demo" (antes: cuenta del primer curso de Jean; ahora: cuenta del segundo curso). Puntos 2 y 3 replicados en la cuenta nueva, raw completo.
- Trusted, capa de detalle completa: 72 meses más `taxi_zones`, raw = detalle en los 73 controles, una ejecución de 3 h 50 min con un job a la vez y 2 workers; una segunda ejecución no lanza jobs.

## 2026-11-15

### punto3-ingesta — topic cerrado (Jean)
- Jean revisó el Punto 3 del Docx en Word y lo aprobó; el topic `punto3-ingesta` queda Done.
- Decidido que la demo final corre en la cuenta de Jean (convención "Cuenta de la demo"): ya tiene raw con 23 meses y la ingesta desplegada.
- Finding nuevo: las subidas de boto3 fallan con `S3UploadFailedError`, no con `ClientError`.
- Revertida la convención "2025-12 reservado para la demo" (antes: 2025-12 se liberaba en vivo en la sustentación; ahora: no hay demo de ingesta en vivo). Liberado e ingerido 2025-12 en la cuenta de Jean en una corrida: HVFHV 511 MiB en 5 s, yellow 4.305.006 filas, green 48.236 filas. Raw: 24 archivos por dataset, 12,4 GiB. Infraestructura apagada y regla deshabilitada al terminar.

### punto4-trusted — topic abierto (Jean)
- Topic nuevo `punto4-trusted` para el Punto 4, diseñado con RePPIT. Research y propuesta escritos. Se eligió la combinación: tres tablas de detalle por servicio con banderas, más una tabla común `viajes`, en la misma pasada, encadenadas desde la ingesta por Step Functions (ruling "Diseño de trusted"). Se descartó la tabla única con cuarentena porque obligaba a decidir P2 y P3 en trusted.

## 2026-11-13

### planificacion — arquitectura de la ingesta y layout de raw (Jean)
- Decidida la ingesta automática del Punto 3 (convención "Ingesta automática"): Lambda para HVFHV, script en la EC2 por SSM para yellow y green, disparo con EventBridge. Se descartó Airflow porque la rúbrica no lo pide, MWAA no está verificado en Learner Lab y montarlo en una EC2 sumaba un servidor más a 6 días de la entrega. También se descartó Glue JDBC para la RDS por la red de VPC sin probar; la EC2 ya llega a MariaDB.
- Decidido el layout de la zona raw (convención "Layout de la zona raw"): un prefijo por dataset con particiones Hive `year=/month=`, un Parquet por mes. Se descartó una sola clave `mes=YYYY-MM` porque filtrar por año es más incómodo.
- Infraestructura del Punto 2 reproducida desde cero en la cuenta de Academy de Jean con los scripts del repo, sin tocar código: `crear_infra.py`, `sembrar.py` y el simulador de 2024-01 a 2024-03 (167.585 filas de green, igual que en la cuenta de David). El estado final es el mismo en las dos cuentas.

### punto3-ingesta — ingesta automática implementada y probada (Jean)
- Topic nuevo `punto3-ingesta`. Desplegada en la cuenta de Jean una regla de EventBridge cada 5 minutos que invoca la Lambda `tlc-ingesta`. La Lambda baja HVFHV por streaming de la TLC a S3 y lanza por SSM la ingesta de la EC2 (yellow desde archivos, green y `taxi_zones` desde MariaDB a Parquet). Todo cae en `raw/` con el layout de la convención.
- Probado en AWS: la primera corrida dejó 12 archivos en 20 s y la segunda no subió nada. En la corrida programada, sin intervención manual, llegaron los 3 archivos de 2024-04 y green 2024-02, recargado con `--forzar`, se reemplazó. Green 2024-01 cuadra con el archivo de la TLC en filas, sumas y fechas.
- Revisión propia (el subagente `revisor` no se pudo lanzar en modo auto por un hook que modifica el prompt): se corrigieron excepciones sin capturar en las subidas y las descargas.
- Finding nuevo: qué permite Academy para EventBridge, Lambda y SSM.
- Liberados e ingeridos 2024-01 a 2025-11 en la cuenta de Jean: el simulador tardó 75 s y la ingesta 2 min 9 s en una sola invocación (19 meses de HVFHV a 5–12 s cada uno). Raw: 23 archivos por dataset, 11,8 GiB. Green cuadra con MariaDB (1.203.357 filas), y `cbd_congestion_fee` de 2025-06 cuadra con la TLC. Convención nueva "2025-12 reservado para la demo".
- Punto 3 del Docx con evidencias: 4 capturas de consola enmascaradas (Lambda, EventBridge, S3, CloudWatch con la corrida automática), 2 figuras de terminal (carga completa y reconciliación) y extractos de código. Figuras también en `punto3-ingesta/evidencias/`. Notas nuevas en Obsidian: runbook de la corrida y dinámica del pipeline, con el guion de la demo.

### Files (proyecto2-sd, branch main)
- `docs/design/CONTEXT.md`, `docs/design/README.md`, `docs/design/findings.md`, `docs/design/planificacion/context.md`, `docs/design/planificacion/current/fuentes-de-datos.md`, `comun/config.py` (modified)
- `punto3-ingesta/` (`raw.py`, `lambda_ingesta.py`, `ec2_ingesta.py`, `desplegar.py`, `ingestar.py`, `test_raw.py`, `README.md`), `docs/design/punto3-ingesta/context.md` (new)

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

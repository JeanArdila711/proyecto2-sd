# punto5-catalogo — Context

**Tracker:** none
**Status:** In progress · **Owner:** Jean

## Orientation

Punto 5 de la rúbrica: tablas SQL sobre `trusted/` en el Glue Data Catalog y en EMR/Hive. Se hizo directo en la cuenta de la demo (convención "Cuenta de la demo"); el plan de que David lo desarrollara en su cuenta sobre una muestra quedó sin efecto (encargo en `archive/encargo.md`). El código, el por qué y los resultados están en `punto5-catalogo/README.md` del repo. Falta: capturas de evidencia (Glue, Athena y EMR) con el ID de cuenta enmascarado, y un `/reppit-review` del diff. Los Puntos 6–8 los implementa un compañero sobre la base `tlc_trusted`.

## Rulings

- **Cómo se cataloga (Jean, 2026-11-16 13:00):** Verdict: per project CONTEXT Conventions ("Catalogación"). Topic detail: base `tlc_trusted`, workgroup de Athena `tlc-consultas` con resultados en `athena/`, Lambda `tlc-catalogo` (nombres en `RECURSOS`).
- **Particiones como string (Jean, 2026-11-16 20:00):** `year`, `month` y `servicio` se declaran `string`, con el texto de la ruta ("01"). Las consultas filtran `year = '2025'`. Evita depender de cómo cada motor castea "01" a entero.
- **Paso Catalogar después de Fallidos (Jean, 2026-11-16 20:00):** la Lambda corre también si algún mes falló, con el error en `$.error_catalogo` y la ejecución en `Fallo`. Va después de `Fallidos` porque la salida del `Map` es una lista y no admite `ResultPath`. Se agrega solo si la Lambda existe.

_Every ruling passes the scope test when it is written (skill `memoria-equipo` § Decisiones). Put a date in the bold label: the checker reads it._

## Journal (newest first)

**2026-11-16, noche (Jean):** Punto 5 implementado y verificado en la cuenta de la demo. `catalogo.py` crea la base, las 5 tablas (tipos del `esquema_detalle` de los controles y de `contrato.viajes()`) y 144 particiones; la segunda corrida no crea nada. `verificar.py`: Athena = controles en todas las particiones (125 MiB escaneados). `emr_hive.py`: un `m5.xlarge` con Hive sobre el Glue Catalog contó lo mismo que los controles y se apagó solo en 778 s; un primer intento falló por la zona de disponibilidad (`findings.md`). El `revisor` no encontró bloqueantes; se aplicaron sus 7 sugerencias. Siguiente: capturas y review. design_check: 0 FAIL, 0 WARN.

**2026-11-16 (Jean):** Topic abierto para David con el encargo (ahora `archive/encargo.md`): muestra de trusted en su cuenta (fase A) y catalogación (fase B).

## Document map

The map is the listing for this folder. One row per file; folders give the lifecycle, this table gives role and load.

| File | Role | Load | What it holds |
|------|------|------|---------------|
| `archive/encargo.md` | referencia (superada) | on-demand | El encargo original para David: muestra en su cuenta, reglas de Glue y EMR. Sin efecto desde que Jean hizo el Punto 5 |

---
name: memoria-equipo
description: Usar en el repo proyecto2-sd al empezar, retomar o cerrar una sesión de trabajo con agentes, y cada vez que se lee o escribe en `docs/design/` — qué leer primero, en qué archivo va un hecho, una decisión o un borrador, cómo abrir o cerrar un topic, registrar un finding y el chequeo de cierre de sesión. Versión de equipo de la memoria del proyecto.
---

# Memoria del proyecto (versión de equipo)

El chat no sobrevive entre sesiones; los archivos sí. Esta skill define dónde guardar el estado del proyecto para que cualquier integrante, con cualquier agente, retome donde quedó el anterior.

La memoria se rompe por dos cosas: **leer de más** (carpetas enteras, historias largas) y **escribir el mismo hecho en varios lugares**, que después se contradicen. Lo evitan tres cosas: un layout fijo, un orden de carga y un solo hogar para cada decisión.

Material de apoyo, en esta misma carpeta. Abrirlo solo cuando el paso lo pide:
- `templates/`: esqueletos de cada archivo. Los encabezados en inglés (`Active Context`, `Conventions`, `Rulings`, `Journal`, `Document map`, `Current state`, `Last updated`, `Status`) los lee el checker: **no traducirlos**.
- `references/rulings.md`: cómo promover o revertir una decisión.
- `references/lifecycle.md`: casos dudosos de en qué carpeta va un archivo.
- `references/session-close.md`: detalle del cierre de sesión.
- `references/examples.md`: versiones correctas e incorrectas de cada archivo.
- `scripts/design_check.py`: chequeos mecánicos, solo lectura.

## Reglas de equipo

1. **Una persona a la vez.** No se trabaja en paralelo sobre la memoria.
2. **Al empezar:** `git pull`. Después, leer L0 y L1 (protocolo de carga) y resumir en 3–4 líneas dónde quedó el proyecto.
3. **Al terminar:** cierre de sesión completo, y commit + push de `docs/design/` junto con el trabajo. Si no se sube, el siguiente arranca con memoria vieja.
4. **El repo es público:** nada de credenciales, IDs de cuenta AWS, `.env` ni llaves en ningún archivo.
5. **El autor va en las decisiones:** cada decisión lleva el nombre de quien la tomó (formato abajo).

## Layout

```
docs/design/
  CONTEXT.md     lo que es verdad ahora en todo el proyecto; la puerta de entrada (L0)
  README.md      resultado y navegación, para humanos
  CHANGELOG.md   historia append-only; se escribe cada sesión, se lee solo si se pide
  findings.md    hechos durables que cruzan topics; solo cuando la tarea toca el tema
  INDEX.md       informes de subagentes reutilizables; antes de explorar o delegar
  <topic>/       una carpeta por pieza de trabajo (slug kebab-case)
    context.md   control: orientación, decisiones, journal, document map (L1)
    handoff.md   opcional: qué falta y por dónde seguir, si el topic quedó a medias
    current/     documentos vigentes: lo único del topic que se carga por defecto
    working/     borradores en curso
    evidence/    material traído de afuera; inmutable
    archive/     superado o gastado; se conserva, nunca está en la ruta de lectura
    assets/      lo que no es markdown
```

La raíz tiene solo los cinco archivos de proyecto y las carpetas de topic. Cada topic tiene `context.md` desde que existe. Una carpeta de ciclo de vida se crea la primera vez que algo entra en ella.

**Un topic se crea cuando alguien va a trabajar una pieza con un plan concreto.** Mientras tanto, el trabajo planeado vive como fila "Planned - no topic" en las Phases del README. No se crean carpetas vacías.

### Dónde va cada frase

| La frase es… | Va en… |
|---|---|
| Un evento fechado: "el {fecha} hicimos X" | `CHANGELOG.md` |
| Un estado superado: "antes era…" | `CHANGELOG.md`, nunca `CONTEXT.md` |
| Lo que es verdad ahora en todo el proyecto (estado, bloqueos) | `CONTEXT.md` Active Context, reemplazando el bloque anterior |
| Una decisión que un topic futuro haría mal sin conocer | `CONTEXT.md` Conventions |
| Una decisión que solo necesita este topic | `<topic>/context.md` § Rulings |
| Lo que hizo una sesión en un topic | `<topic>/context.md` Journal |
| Un resultado durable (qué se construyó, cifras clave) | `README.md` |
| Un hecho que otros topics necesitan | `findings.md` |
| Un informe de subagente que conviene reusar | `INDEX.md` + el informe en `<topic>/evidence/` |

La prueba: si la frase describe el pasado, va al CHANGELOG; si describe el ahora, va a CONTEXT. CONTEXT nunca narra cómo llegó a donde está.

## Protocolo de carga

Leer en este orden y parar apenas la tarea esté orientada:

| Nivel | Qué |
|---|---|
| L0 | `CONTEXT.md` |
| L1 | `<topic>/context.md` del topic activo |
| L2 | Lo que su document map marca `always`; `INDEX.md` antes de explorar o delegar |
| L3 | Solo lo que la tarea nombra. `findings.md` solo si la tarea toca un tema que lista |

No abrir `evidence/`, `archive/` ni `CHANGELOG.md` salvo que la tarea nombre el archivo. Nunca listar una carpeta de topic entera: para eso está el document map.

Si una decisión, una cifra o el alcance se contradicen entre archivos, **parar y preguntar**; no elegir uno en silencio. La salida de un comando recién corrido le gana a cualquier documento.

## Archivos actuales y chicos

**Un solo bloque de estado.** Cuando cambia el estado del proyecto, en la misma sesión:
1. Escribir la entrada del CHANGELOG.
2. Borrar el bloque viejo de Active Context, pasando antes a esa entrada cualquier hecho que el CHANGELOG no tenga.
3. Escribir el bloque nuevo y actualizar `Last updated`.

Nunca se apila un bloque "Prior state" debajo del actual.

**Journal acotado.** El journal de cada `context.md` va del más nuevo al más viejo, con 6–8 bloques. Pasado el tope, los más viejos se colapsan en una lista (`- YYYY-MM-DD: resultado`).

| Archivo | Meta | Compactar si… |
|---|---|---|
| `CONTEXT.md` | ≤ ~80 líneas | > 100 líneas o algún "Prior state" |
| Active Context | ≤ ~15 líneas | más de un bloque de estado |
| `<topic>/context.md` | ≤ ~120 líneas | > 150 líneas o > 8 bloques de journal |

## Decisiones

Una decisión es algo que el trabajo posterior debe respetar. Vive en **un solo lugar**:
- **De proyecto** → `CONTEXT.md` § Conventions.
- **De topic** → `<topic>/context.md` § Rulings.

Los demás archivos la nombran y no repiten el veredicto.

**Prueba de alcance:** ¿un topic futuro se equivocaría sin saber esto? Sí → Conventions. No → Rulings del topic. Si hay duda, preguntar al equipo.

```markdown
- **{Nombre} (in force {YYYY-MM-DD}; owner {persona}; source {topic}):** {veredicto, 1-3 líneas}.   ← Conventions
- **{Nombre} ({persona}, {YYYY-MM-DD HH:MM}):** {veredicto}.                                         ← Rulings del topic
```

El checker lee la fecha de la etiqueta en negrita. Para promover o revertir una decisión, seguir `references/rulings.md`; los dos caminos terminan con un `grep` de la frase vieja en `docs/design/`.

## Carpetas de ciclo de vida

Para archivar un documento, preguntar en orden; la primera respuesta afirmativa manda:
1. ¿Viene de una fuente externa (export, captura, informe de subagente)? → `evidence/`
2. ¿Es un borrador en curso? → `working/`
3. ¿Está superado o gastado? → `archive/`
4. Si no, es vigente y nuestro → `current/`

Se archiva en vez de borrar. `evidence/` y `archive/` no se editan.

**Document map:** una fila por archivo del topic, con ruta, rol (entregable, concepto, referencia, borrador), carga (`always` u `on-demand`) y una línea sobre qué contiene.

## Findings

Solo entra lo que sirve a otros topics. Lo específico de un topic va en su `context.md`. Formato en `templates/findings.md`, con etiqueta:
- `[hecho]`: observado y verificado en este proyecto, con fecha.
- `[regla]`: qué hacer, con su disparador y la evidencia.
- `[suposición]`: sin verificar, pendiente de comprobar.

Al agregar uno, actualizar en `CONTEXT.md` la línea `findings.md — N entries, last {fecha}`.

## Informes de subagentes (INDEX.md)

Si un subagente deja un informe largo que va a servir en otras sesiones, guardarlo en `<topic>/evidence/` y agregar una fila a `INDEX.md` con el commit (`git rev-parse --short HEAD`) y las rutas que cubre. Antes de explorar, buscar el tema en `INDEX.md`: si `git diff --stat <commit> -- <cubre>` sale vacío, el informe está vigente.

## Flujos

### Abrir un topic
1. Crear `<topic>/context.md` desde `templates/topic-context.md`, con la tarea y las restricciones en Orientation.
2. Agregarlo a "Active topics" de `CONTEXT.md` y a la tabla Topics del README; cambiar su fila de Phases.
3. Una línea en el CHANGELOG.

### Después de trabajar
1. Entrada fechada en el CHANGELOG (mirar antes las de arriba para no duplicar).
2. Cada documento nuevo a su carpeta y con su fila en el document map.
3. Cada decisión nueva a su hogar, después de pasarla por la prueba de alcance.
4. Si cambió el estado, reemplazar el bloque de Active Context.
5. Actualizar las tablas Documents, Topics y Open decisions del README.

### Pausar un topic a medias
Escribir en `<topic>/handoff.md` qué falta y por dónde seguir. Es lo primero que lee quien retome.

### Cerrar un topic
1. Decisiones a su hogar, entregable a `current/`, borradores gastados a `archive/` (`git mv`).
2. `**Status:**` del topic a `Done` (o `Cancelled` / `Superseded`).
3. Reemplazar Active Context y sacar el topic de los activos.
4. Actualizar el README y agregar una entrada al CHANGELOG.
5. Cierre de sesión.

## Cierre de sesión

Toda sesión que escribió en `docs/design/` termina así (detalle en `references/session-close.md`):

1. **Triage** de cada documento producido: se queda (`current/` + su fila en el map), sigue en curso (`working/`), se archiva (`archive/`) o se descarta (solo borradores que no concluyen nada).
2. **Findings:** si se aprendió un hecho que cruza topics, agregarlo y actualizar el puntero en CONTEXT.
3. **Registro:** document map al día y una línea en el CHANGELOG.
4. **Chequeo:**
   ```bash
   python3 .claude/skills/memoria-equipo/scripts/design_check.py docs/design
   ```
   Corregir cada FAIL. Revisar además lo que el script no ve: que Active Context nombre el estado más reciente, que los estados del README coincidan con los topics y que cada decisión de la sesión haya pasado la prueba de alcance.
5. **Commit + push** de `docs/design/` junto con el trabajo de la sesión.

## Errores comunes

| Error | Por qué falla |
|---|---|
| Leer toda `docs/design/` al arrancar | Carga topics cerrados y gasta contexto en lo que no importa |
| Repetir el veredicto de una decisión en otro archivo | Las copias se separan y la próxima sesión obedece la vieja |
| Apilar un "Prior state" en CONTEXT | CONTEXT se carga siempre; el historial va al CHANGELOG |
| Poner en `findings.md` algo propio de un topic | `findings.md` es para lo que sirve a otros topics |
| Promover a `current/` un borrador sin terminar | Pone en la ruta de lectura algo que no es verdad todavía |
| Borrar un topic cerrado | Es el historial; se archiva |
| Terminar sin commit + push | El siguiente integrante arranca con memoria vieja |
| Crear topics vacíos "para después" | Carpetas sin plan que nadie mantiene |

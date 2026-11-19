"""Punto 8: tablero de P1–P6 en Streamlit. Consume la API del Punto 8 (API Gateway → Lambda → resultados en S3).

La URL de la API la deja desplegar.py en api_url.txt, junto a este archivo.
  streamlit run app.py
"""
from pathlib import Path

import altair as alt
import streamlit as st

import analisis as a

API = Path(__file__).with_name("api_url.txt").read_text().strip()
TINTA, SECUNDARIO, PAPEL, LINEA = "#1b1b1a", "#5c5b56", "#f6f5f1", "#d9d7cf"
GRIS_2024 = "#a3a19a"

st.set_page_config(page_title="TLC NYC 2024–2025", page_icon="🚕", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500&family=Public+Sans:wght@400;600;750&display=swap');
html, body, [class*="css"], .stMarkdown, .stTabs, .stSelectbox, .stRadio { font-family: 'Public Sans', sans-serif; }
.block-container { padding-top: 2.5rem; max-width: 1180px; }
.franja { height: 6px; width: 72px; background: #f2b705; margin-bottom: 14px; }
.titulo { font-size: 2.1rem; font-weight: 750; letter-spacing: -0.02em; line-height: 1.1; margin: 0; }
.bajada { color: #5c5b56; font-size: 1rem; margin: 6px 0 4px; max-width: 72ch; }
.pregunta { font-size: 1.3rem; font-weight: 600; line-height: 1.3; margin: 8px 0 4px; max-width: 70ch; }
.hallazgo { border-left: 3px solid #1b1b1a; padding: 2px 0 2px 12px; margin: 10px 0 18px; max-width: 75ch; }
[data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; font-size: 1.7rem; }
[data-testid="stMetricLabel"] p { color: #5c5b56; font-size: 0.85rem; }
.fuente { color: #5c5b56; font-size: 0.8rem; margin-top: 6px; }
.fuente code { font-size: 0.78rem; }
</style>""", unsafe_allow_html=True)


@st.cache_data(ttl=600, show_spinner="Consultando la API…")
def datos(pregunta):
    return a.leer(API, pregunta)


def escala(nombres):
    """Color fijo por compañía, sin importar cuántas aparezcan en la gráfica."""
    orden = [a.NOMBRES[c] for c in a.COMPANIAS if a.NOMBRES[c] in set(nombres)]
    return alt.Scale(domain=orden, range=[a.COLORES[c] for c in a.COMPANIAS if a.NOMBRES[c] in orden])


def tema(grafica, alto=340):
    # padding derecho: espacio para el nombre de la compañía al final de cada línea
    return (grafica.properties(height=alto, padding={"left": 5, "top": 5, "bottom": 5, "right": 110})
            .configure(font="Public Sans", background=PAPEL)
            .configure_view(stroke=None)
            .configure_axis(labelColor=SECUNDARIO, titleColor=SECUNDARIO, gridColor=LINEA, domainColor=LINEA,
                            tickColor=LINEA, labelFontSize=12, titleFontSize=12, titleFontWeight=400)
            .configure_legend(orient="top", title=None, labelColor=TINTA, labelFontSize=12, symbolStrokeWidth=3))


def lineas(df, x, y, titulo_x, titulo_y, formato, tipo_x="O", alto=340):
    """Una línea por compañía con tooltip y la etiqueta de la compañía al final de cada línea."""
    color = alt.Color("nombre:N", scale=escala(df["nombre"]))
    eje_x = alt.Axis(labelAngle=0, format="%m/%Y", tickCount="month") if tipo_x == "T" else alt.Axis(labelAngle=0)
    base = alt.Chart(df).encode(x=alt.X(f"{x}:{tipo_x}", title=titulo_x, axis=eje_x),
                                y=alt.Y(f"{y}:Q", title=titulo_y, scale=alt.Scale(zero=False),
                                        axis=alt.Axis(format=formato)),
                                color=color)
    cerca = alt.selection_point(fields=[x], nearest=True, on="pointerover", empty=False)
    linea = base.mark_line(strokeWidth=2.5, interpolate="monotone")
    puntos = base.mark_point(size=70, filled=True, strokeWidth=2, stroke=PAPEL).encode(
        opacity=alt.condition(cerca, alt.value(1), alt.value(0)),
        tooltip=[alt.Tooltip("nombre:N", title="Compañía"),
                 alt.Tooltip(f"{x}:{tipo_x}", title=titulo_x, **({"format": "%m/%Y"} if tipo_x == "T" else {})),
                 alt.Tooltip(f"{y}:Q", title=titulo_y, format=formato),
                 alt.Tooltip("viajes:Q", title="Viajes", format=",")]).add_params(cerca)
    ultimo = df[df[x] == df[x].max()]
    etiquetas = alt.Chart(ultimo).mark_text(align="left", dx=8, fontSize=12, fontWeight=600).encode(
        x=f"{x}:{tipo_x}", y=f"{y}:Q", text="nombre:N", color=color)
    regla = alt.Chart(df).mark_rule(color=LINEA).encode(x=f"{x}:{tipo_x}").transform_filter(cerca)
    return tema(alt.layer(regla, linea, puntos, etiquetas), alto)


def barras_h(df, y, x, titulo_x, formato, color=TINTA, orden="-x", alto=None):
    alto = alto or max(120, 30 * len(df))
    b = alt.Chart(df).encode(
        y=alt.Y(f"{y}:N", sort=orden, title=None, axis=alt.Axis(labelLimit=260, labelOverlap=False)),
        x=alt.X(f"{x}:Q", title=titulo_x, axis=alt.Axis(format=formato)),
        tooltip=[alt.Tooltip(f"{y}:N", title=" "), alt.Tooltip(f"{x}:Q", title=titulo_x, format=formato),
                 alt.Tooltip("viajes:Q", title="Viajes", format=",")])
    texto = b.mark_text(align="left", dx=6, fontSize=12, color=TINTA).encode(
        text=alt.Text(f"{x}:Q", format=formato))
    return tema(alt.layer(b.mark_bar(color=color, cornerRadiusEnd=4, height=18), texto), alto)


def encabezado(pregunta, titulo):
    st.markdown(f'<p class="pregunta">{titulo}</p>', unsafe_allow_html=True)


def hallazgo(texto):
    st.markdown(f'<div class="hallazgo">{texto}</div>', unsafe_allow_html=True)


def tabla(df, pregunta):
    with st.expander("Ver la tabla"):
        st.dataframe(df, hide_index=True, use_container_width=True)
    st.markdown(f'<p class="fuente">Fuente: <code>GET {API}/resultados/{pregunta}</code> · '
                'TLC Trip Record Data, 2024–2025</p>', unsafe_allow_html=True)


def cifra(col, etiqueta, valor, nota):
    """Cifra clave con una nota debajo, sin la flecha de variación de st.metric (la nota no es una variación)."""
    col.metric(etiqueta, valor)
    col.caption(nota)


def pct(v):
    return f"{v:.1f} %".replace(".", ",")


def usd(v):
    return f"US$ {v:.2f}".replace(".", ",")


# ------------------------------------------------------------------ encabezado
st.markdown('<div class="franja"></div><p class="titulo">Taxis y apps en Nueva York, 2024–2025</p>'
            '<p class="bajada">Seis preguntas respondidas con los registros de viajes de la TLC: taxis amarillos y '
            'verdes, Uber y Lyft. Más de 570 millones de viajes, procesados en AWS y servidos por API Gateway.</p>',
            unsafe_allow_html=True)

tabs = st.tabs(["P1 · Mercado", "P2 · Costo por milla", "P3 · Pago al conductor", "P4 · Espera",
                "P5 · Propinas", "P6 · Cobro por congestión"])

# ------------------------------------------------------------------ P1
with tabs[0]:
    titulo, df = datos("p1")
    encabezado("p1", titulo)
    boroughs = [a.TODA_LA_CIUDAD] + sorted(b for b in df["borough"].unique() if b != "EWR")
    borough = st.radio("Borough", boroughs, horizontal=True, key="b1", label_visibility="collapsed")
    anual = a.p1_por_anio(df, borough).fillna(0)
    # El último año con datos y el anterior, si existe: con una muestra de un solo año no hay comparación
    anios = sorted(anual.columns)
    ultimo, previo = anios[-1], (anios[-2] if len(anios) > 1 else None)
    cols = st.columns(4)
    for col, c in zip(cols, a.COMPANIAS):
        if c in anual.index:
            v = anual.loc[c, ultimo]
            delta = (f"{v - anual.loc[c, previo]:+.1f}".replace(".", ",") + f" pp vs. {previo}") if previo else None
            col.metric(f"{a.NOMBRES[c]}, {ultimo}", pct(v), delta)
    lider = anual[ultimo].idxmax()
    lugar = borough.lower() if borough == a.TODA_LA_CIUDAD else borough
    texto = f"En {lugar}, {a.NOMBRES[lider]} se lleva {pct(anual.loc[lider, ultimo])} de los viajes de {ultimo}."
    if previo and "yellow" in anual.index:
        texto += (f" El taxi amarillo pasó de {pct(anual.loc['yellow', previo])} a "
                  f"{pct(anual.loc['yellow', ultimo])}.")
    hallazgo(texto)
    serie = a.p1_participacion(df, borough)
    st.altair_chart(lineas(serie, "fecha", "participacion", "Mes", "Participación (%)", ".1f", tipo_x="T"),
                    use_container_width=True)
    tabla(df, "p1")

# ------------------------------------------------------------------ P2
with tabs[1]:
    titulo, df = datos("p2")
    encabezado("p2", titulo)
    boroughs = [a.TODA_LA_CIUDAD] + sorted(b for b in df["borough"].unique() if b != "EWR")
    borough = st.radio("Borough", boroughs, horizontal=True, key="b2", label_visibility="collapsed")
    total = a.p2_costo(df, ["compania"], borough).set_index("compania")
    cols = st.columns(3)
    for col, c in zip(cols, ["yellow", "uber", "lyft"]):
        if c in total.index:
            col.metric(f"{a.NOMBRES[c]}, por milla", usd(total.loc[c, "costo_por_milla"]))
    caro = total["costo_por_milla"].idxmax()
    hallazgo(f"Tarifa base más recargos, sin peajes ni propina. {a.NOMBRES[caro]} es el más caro por milla "
             f"({usd(total.loc[caro, 'costo_por_milla'])}). Se excluyen viajes de más de 100 millas: en el taxi "
             "amarillo hay registros con miles de millas que hunden el promedio.")
    st.altair_chart(lineas(a.p2_costo(df, ["compania", "hora"], borough), "hora", "costo_por_milla",
                           "Hora del día", "USD por milla", "$.2f"), use_container_width=True)
    tabla(df, "p2")

# ------------------------------------------------------------------ P3
with tabs[2]:
    titulo, df = datos("p3")
    encabezado("p3", titulo)
    boroughs = sorted(b for b in df["borough"].unique() if b != "EWR")
    borough = st.radio("Borough", boroughs, index=boroughs.index("Manhattan"), horizontal=True, key="b3",
                       label_visibility="collapsed")
    serie = a.p3_por_hora(df, borough)
    cols = st.columns(2)
    for col, c in zip(cols, ["uber", "lyft"]):
        s = serie[serie["compania"] == c]["pct"]
        cifra(col, f"{a.NOMBRES[c]}: el conductor recibe", f"{pct(s.min())} – {pct(s.max())}",
                   "según la hora")
    hallazgo("Pago al conductor más propina, sobre todo lo que paga el pasajero (tarifa, peajes, recargos, "
             "impuestos y propina). Las dos apps le pagan al conductor una proporción muy parecida.")
    st.altair_chart(lineas(serie, "hora", "pct", "Hora del día", "Le llega al conductor (%)", ".1f"),
                    use_container_width=True)
    tabla(df, "p3")

# ------------------------------------------------------------------ P4
with tabs[3]:
    titulo, df = datos("p4")
    encabezado("p4", titulo)
    boroughs = [a.TODA_LA_CIUDAD] + sorted(b for b in df["borough"].unique() if b != "EWR")
    borough = st.radio("Borough", boroughs, horizontal=True, key="b4", label_visibility="collapsed")
    total = a.p4_espera(df, ["compania"], borough).set_index("compania")
    cols = st.columns(4)
    for c, (c1, c2) in zip(["uber", "lyft"], [cols[0:2], cols[2:4]]):
        c1.metric(f"{a.NOMBRES[c]}: espera promedio", f"{total.loc[c, 'espera_min']:.1f} min".replace(".", ","))
        c2.metric(f"{a.NOMBRES[c]}: más de 10 min", pct(total.loc[c, "pct_mas_10"]))
    medida = st.radio("Medida", ["Espera promedio", "Esperas de más de 10 min"], horizontal=True, key="m4")
    hallazgo("Desde que se pide el viaje hasta que recogen al pasajero. No incluye esperas de más de una hora, "
             "que corresponden a viajes reservados con anticipación.")
    serie = a.p4_espera(df, ["compania", "hora"], borough)
    if medida == "Espera promedio":
        grafica = lineas(serie, "hora", "espera_min", "Hora del día", "Minutos", ".1f")
    else:
        grafica = lineas(serie, "hora", "pct_mas_10", "Hora del día", "Esperas de más de 10 min (%)", ".1f")
    st.altair_chart(grafica, use_container_width=True)
    tabla(df, "p4")

# ------------------------------------------------------------------ P5
with tabs[4]:
    titulo, df = datos("p5")
    encabezado("p5", titulo)
    aero = a.p5_dimension(df, "aeropuerto").set_index("valor")
    dist = a.p5_dimension(df, "distancia")
    cols = st.columns(3)
    cifra(cols[0], "Propina, viajes al aeropuerto", pct(aero.loc["aeropuerto", "propina_pct"]),
                   usd(aero.loc["aeropuerto", "propina_promedio"]) + " en promedio")
    cifra(cols[1], "Propina, resto de viajes", pct(aero.loc["no aeropuerto", "propina_pct"]),
                   usd(aero.loc["no aeropuerto", "propina_promedio"]) + " en promedio")
    corto, largo = dist.iloc[0], dist.iloc[-1]
    cifra(cols[2], "Propina, viajes de menos de 1 milla", pct(corto["propina_pct"]),
                   f"{pct(largo['propina_pct'])} en los de 20 a 100 mi")
    hallazgo("Propina como porcentaje de la tarifa, solo pagos con tarjeta (en efectivo no se registra). "
             "Los viajes cortos dejan proporcionalmente más; los largos y los del aeropuerto dejan más dólares "
             "pero menos porcentaje. La hora casi no lo mueve. Por zona, Manhattan ronda el 24 %; en algunas "
             "zonas de Brooklyn entre el 97 y el 99 % de los viajes con tarjeta registra propina 0, y con los "
             "datos de la TLC no se puede saber si no se dejó propina o si no quedó registrada.")
    izq, der = st.columns(2)
    with izq:
        st.caption("Por distancia")
        st.altair_chart(barras_h(dist.assign(valor=dist["valor"].str[3:]), "valor", "propina_pct",
                                 "Propina (% de la tarifa)", ".1f", orden=None), use_container_width=True)
    with der:
        st.caption("Por hora del pickup")
        hora = a.p5_dimension(df, "hora").assign(hora=lambda d: d["valor"].astype(int))
        st.altair_chart(tema(alt.Chart(hora).mark_bar(color=TINTA, cornerRadiusEnd=3).encode(
            x=alt.X("hora:O", title="Hora", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("propina_pct:Q", title="Propina (%)"),
            tooltip=[alt.Tooltip("hora:O", title="Hora"),
                     alt.Tooltip("propina_pct:Q", title="Propina (%)", format=".1f"),
                     alt.Tooltip("viajes:Q", title="Viajes", format=",")]), 200), use_container_width=True)
    st.caption("Zonas de origen con la propina más alta y más baja (con al menos 20.000 viajes)")
    st.altair_chart(barras_h(a.p5_zonas(df), "valor", "propina_pct", "Propina (% de la tarifa)", ".1f"),
                    use_container_width=True)
    tabla(df, "p5")

# ------------------------------------------------------------------ P6
with tabs[5]:
    titulo, df = datos("p6")
    encabezado("p6", titulo)
    anios_p6 = set(df["year"]) if len(df) else set()
    if not {"2024", "2025"} <= anios_p6:
        # Sin 2024 y 2025 no hay antes y después del cobro (por ejemplo, una muestra solo de 2024).
        # P6 es la última pestaña: st.stop() solo corta lo que queda de ella.
        st.info("Esta pregunta compara 2024 con 2025 y los datos cargados no tienen los dos años "
                f"(hay: {', '.join(sorted(anios_p6)) or 'ninguno'}). Con 2024 y 2025 completos aparece la comparación.")
        tabla(df, "p6")
        st.stop()
    comp = a.p6_companias(df).set_index("compania")
    mensual = a.p6_mensual(df)
    total24, total25 = mensual["2024"].sum(), mensual["2025"].sum()
    cols = st.columns(4)
    cols[0].metric("Viajes hacia la zona, 2025", f"{total25 / 1e6:.1f} M".replace(".", ","),
                   f"{100 * (total25 / total24 - 1):+.1f}".replace(".", ",") + " % vs. 2024")
    for col, c in zip(cols[1:], ["yellow", "uber", "lyft"]):
        cifra(col, a.NOMBRES[c], f"{comp.loc[c, 'variacion']:+.1f} %".replace(".", ","),
                   f"{pct(comp.loc[c, 'part_2025'])} del total en 2025")
    hallazgo("La zona de cobro son 38 zonas de Manhattan derivadas de los datos (las que cobran el cargo en la "
             "mayoría de sus viajes internos). El total de viajes hacia la zona casi no cambió, pero el reparto "
             "sí: el taxi amarillo y Lyft ganaron viajes y Uber perdió.")
    largo = mensual.melt(id_vars="month", value_vars=["2024", "2025"], var_name="anio", value_name="viajes")
    largo["mes"] = largo["month"].astype(int)
    barras = alt.Chart(largo).mark_bar(cornerRadiusEnd=3).encode(
        x=alt.X("mes:O", title="Mes", axis=alt.Axis(labelAngle=0)),
        xOffset="anio:N",
        y=alt.Y("viajes:Q", title="Viajes hacia la zona", axis=alt.Axis(format="~s")),
        color=alt.Color("anio:N", title=None, scale=alt.Scale(domain=["2024", "2025"],
                                                              range=[GRIS_2024, TINTA])),
        tooltip=[alt.Tooltip("anio:N", title="Año"), alt.Tooltip("mes:O", title="Mes"),
                 alt.Tooltip("viajes:Q", title="Viajes", format=",")])
    st.altair_chart(tema(barras, 300), use_container_width=True)
    st.caption("Variación de viajes hacia la zona por compañía, 2025 frente a 2024")
    var = comp.reset_index()[["compania", "nombre", "variacion", "2025"]].rename(columns={"2025": "viajes"})
    orden = var.sort_values("variacion", ascending=False)["nombre"].tolist()  # el mismo en las tres capas
    st.altair_chart(tema(alt.Chart(var).mark_bar(cornerRadiusEnd=4, height=22).encode(
        y=alt.Y("nombre:N", sort=orden, title=None),
        x=alt.X("variacion:Q", title="Variación (%)", axis=alt.Axis(format="+.0f")),
        color=alt.Color("nombre:N", scale=escala(var["nombre"]), legend=None),
        tooltip=[alt.Tooltip("nombre:N", title="Compañía"), alt.Tooltip("variacion:Q", title="Variación (%)",
                                                                        format="+.1f"),
                 alt.Tooltip("viajes:Q", title="Viajes 2025", format=",")]) +
        # La cifra va afuera del extremo de cada barra: a la derecha si crece, a la izquierda si cae
        alt.Chart(var[var["variacion"] >= 0]).mark_text(dx=6, align="left", fontSize=12, color=TINTA).encode(
            y=alt.Y("nombre:N", sort=orden), x="variacion:Q", text=alt.Text("variacion:Q", format="+.1f")) +
        alt.Chart(var[var["variacion"] < 0]).mark_text(dx=-6, align="right", fontSize=12, color=TINTA).encode(
            y=alt.Y("nombre:N", sort=orden), x="variacion:Q", text=alt.Text("variacion:Q", format="+.1f")),
        170), use_container_width=True)
    tabla(df, "p6")

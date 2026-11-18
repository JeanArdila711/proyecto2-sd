#!/usr/bin/env python3
"""Punto 8: gráficas estáticas de P1–P6 (PNG, matplotlib) para el documento de entrega.

Lee los datos de la misma API que usa Streamlit (GET /resultados/{pregunta}) y prepara cada pregunta con
app/analisis.py, así que la app y las gráficas muestran exactamente los mismos números.

  python punto8-visualizacion-app/graficas.py            # busca la API tlc-resultados en la cuenta
  python punto8-visualizacion-app/graficas.py --api URL  # sin credenciales de AWS
Deja graficas/p1.png ... graficas/p6.png.
"""
import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mt  # noqa: E402

DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(DIR.parent), str(DIR / "app")]
import analisis as a  # noqa: E402

SALIDA = DIR / "graficas"
TINTA, SECUNDARIO, PAPEL, LINEA, GRIS_2024 = "#1b1b1a", "#5c5b56", "#f6f5f1", "#d9d7cf", "#a3a19a"
plt.rcParams.update({
    "figure.facecolor": PAPEL, "axes.facecolor": PAPEL, "savefig.facecolor": PAPEL, "font.size": 10,
    "font.family": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "axes.edgecolor": LINEA, "axes.labelcolor": SECUNDARIO, "xtick.color": SECUNDARIO, "ytick.color": SECUNDARIO,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": LINEA, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
    "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlecolor": TINTA,
})


def es(texto):
    """Coma decimal, como en el resto del proyecto."""
    return texto.replace(".", ",")


def lineas(ax, df, x, y, companias, formato="{:.1f}"):
    """Una línea por compañía con su nombre y su último valor al final (identidad nunca solo por color)."""
    for c in companias:
        s = df[df["compania"] == c].sort_values(x)
        if s.empty:
            continue
        ax.plot(s[x], s[y], color=a.COLORES[c], linewidth=2.2, solid_capstyle="round")
        ultimo = s.iloc[-1]
        ax.annotate(f"{a.NOMBRES[c]} {es(formato.format(ultimo[y]))}", (ultimo[x], ultimo[y]),
                    xytext=(6, 0), textcoords="offset points", va="center", color=TINTA, fontsize=9)


def guardar(fig, nombre, titulo, pie):
    fig.suptitle(titulo, x=0.01, ha="left", fontsize=13, fontweight="bold", color=TINTA)
    fig.text(0.01, 0.01, pie, fontsize=8, color=SECUNDARIO)
    fig.tight_layout(rect=(0, 0.04, 0.93, 0.95))
    fig.savefig(SALIDA / nombre, dpi=200)
    plt.close(fig)
    print(f"graficas/{nombre}")


def p1(df):
    fig, ax = plt.subplots(figsize=(10, 4.6))
    s = a.p1_participacion(df)
    lineas(ax, s, "fecha", "participacion", a.COMPANIAS, "{:.1f} %")
    ax.set_ylabel("Participación de los viajes (%)")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%m/%Y"))
    guardar(fig, "p1.png", "P1. Participación de mercado por mes, toda la ciudad",
            "Viajes por compañía sobre el total del mes. Detalle por borough en la app. Fuente: TLC, 2024–2025.")


def p2(df):
    fig, ax = plt.subplots(figsize=(10, 4.6))
    lineas(ax, a.p2_costo(df, ["compania", "hora"]), "hora", "costo_por_milla", ["yellow", "uber", "lyft"],
           "US$ {:.2f}")
    ax.set_xlabel("Hora del pickup")
    ax.set_ylabel("USD por milla")
    ax.set_xticks(range(0, 24, 2))
    guardar(fig, "p2.png", "P2. Costo por milla según la hora: taxi amarillo frente a Uber y Lyft",
            "(Tarifa base + recargos) / millas, sin peajes ni propina; viajes de hasta 100 millas. "
            "Fuente: TLC, 2024–2025.")


def p3(df):
    fig, ax = plt.subplots(figsize=(10, 4.6))
    lineas(ax, a.p3_por_hora(df, "Manhattan"), "hora", "pct", ["uber", "lyft"], "{:.1f} %")
    ax.set_xlabel("Hora del pickup")
    ax.set_ylabel("Le llega al conductor (%)")
    ax.set_xticks(range(0, 24, 2))
    guardar(fig, "p3.png", "P3. Porcentaje de lo que paga el pasajero que recibe el conductor, Manhattan",
            "(Pago al conductor + propina) / todo lo que paga el pasajero. Otros boroughs en la app. "
            "Fuente: TLC, 2024–2025.")


def p4(df):
    fig, ax = plt.subplots(figsize=(10, 4.6))
    lineas(ax, a.p4_espera(df, ["compania", "hora"]), "hora", "espera_min", ["uber", "lyft"], "{:.1f} min")
    ax.set_xlabel("Hora del pickup")
    ax.set_ylabel("Espera promedio (min)")
    ax.set_xticks(range(0, 24, 2))
    guardar(fig, "p4.png", "P4. Espera desde la solicitud hasta el pickup, toda la ciudad",
            "Esperas de hasta una hora (las más largas son viajes reservados). Fuente: TLC, 2024–2025.")


def p5(df):
    fig, (izq, der) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1, 1.3]})
    dist = a.p5_dimension(df, "distancia")
    etiquetas = dist["valor"].str[3:]
    izq.barh(etiquetas, dist["propina_pct"], color=TINTA, height=0.6)
    izq.invert_yaxis()
    izq.set_title("Por distancia")
    zonas = a.p5_zonas(df, n=5).sort_values("propina_pct")
    der.barh(zonas["valor"], zonas["propina_pct"], color=[TINTA if g == "Más alta" else GRIS_2024
                                                          for g in zonas["grupo"]], height=0.6)
    der.set_title("Zonas de origen con la propina más alta y más baja")
    for ax, valores in ((izq, dist["propina_pct"]), (der, zonas["propina_pct"])):
        ax.grid(axis="y", visible=False)
        ax.grid(axis="x", visible=True)
        ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, _: f"{v:.0f} %"))
        for i, v in enumerate(valores):
            ax.text(v + 0.3, i, es(f"{v:.1f} %"), va="center", fontsize=8, color=TINTA)
    guardar(fig, "p5.png", "P5. Propina en taxi amarillo como porcentaje de la tarifa",
            "Solo pagos con tarjeta. Zonas con al menos 20.000 viajes. Fuente: TLC, 2024–2025.")


def p6(df):
    fig, (izq, der) = plt.subplots(1, 2, figsize=(11, 4.6), gridspec_kw={"width_ratios": [1.6, 1]})
    m = a.p6_mensual(df)
    x = range(len(m))
    izq.bar([i - 0.2 for i in x], m["2024"] / 1e6, width=0.38, color=GRIS_2024, label="2024")
    izq.bar([i + 0.2 for i in x], m["2025"] / 1e6, width=0.38, color=TINTA, label="2025")
    izq.set_xticks(list(x), [int(v) for v in m["month"]])
    izq.set_xlabel("Mes")
    izq.set_ylabel("Viajes hacia la zona (millones)")
    izq.legend(frameon=False, loc="upper left", ncol=2, bbox_to_anchor=(0, 1.02))
    izq.set_ylim(0, m[["2024", "2025"]].max().max() / 1e6 * 1.18)
    izq.set_title("Viajes hacia la zona de cobro por mes")
    c = a.p6_companias(df)
    c = c[c["compania"] != "green"].sort_values("variacion")
    der.barh(c["nombre"], c["variacion"], color=[a.COLORES[k] for k in c["compania"]], height=0.55)
    der.axvline(0, color=SECUNDARIO, linewidth=0.8)
    der.grid(axis="y", visible=False)
    der.grid(axis="x", visible=True)
    for i, v in enumerate(c["variacion"]):
        der.text(v + (0.6 if v >= 0 else -0.6), i, es(f"{v:+.1f} %"), va="center",
                 ha="left" if v >= 0 else "right", fontsize=9, color=TINTA)
    der.set_title("Variación 2025 frente a 2024 por compañía")
    der.set_xlim(min(c["variacion"].min() * 2.1, -5), c["variacion"].max() * 1.5)  # aire para las cifras
    der.tick_params(axis="y", length=0)
    guardar(fig, "p6.png", "P6. Viajes hacia la zona de cobro por congestión, 2024 frente a 2025",
            "Zona de cobro: 38 zonas de Manhattan derivadas de los datos de 2025. El cobro empezó el 5 de enero "
            "de 2025. Fuente: TLC.")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--api", help="URL base de la API (por defecto la de la API tlc-resultados de la cuenta)")
    args = p.parse_args()
    api = args.api
    if not api:
        from comun import config
        from comun.config import RECURSOS as R
        apis = config.sesion(config.cargar()).client("apigatewayv2").get_apis()["Items"]
        api = next(x["ApiEndpoint"] for x in apis if x["Name"] == R["api_resultados"])
    SALIDA.mkdir(exist_ok=True)
    for nombre, funcion in (("p1", p1), ("p2", p2), ("p3", p3), ("p4", p4), ("p5", p5), ("p6", p6)):
        funcion(a.leer(api, nombre)[1])


if __name__ == "__main__":
    main()

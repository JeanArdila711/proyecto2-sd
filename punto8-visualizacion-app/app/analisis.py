"""Datos de cada pregunta listos para graficar. Lo usan app.py (Streamlit, en la EC2) y graficas.py (PNG locales).

Todo sale de la API del Punto 8 (GET /resultados/{pregunta}), no de S3 ni de Athena. Las agregaciones son
exactas: P1 y P6 suman conteos; P2 recompone la tarifa total como costo_por_milla × millas, así que vuelve a
ser razón de sumas (convención "Métrica de P2"); P4 pondera por viajes, que es exacto para un promedio.
P3 no se puede agregar entre boroughs (falta el total pagado de cada grupo), así que se muestra por borough.
"""
import json
import urllib.request

import pandas as pd

COMPANIAS = ["uber", "lyft", "yellow", "green"]  # orden fijo: el color sigue a la compañía, no al ranking
COLORES = {"uber": "#2a78d6", "lyft": "#e87ba4", "yellow": "#eda100", "green": "#008300"}
NOMBRES = {"uber": "Uber", "lyft": "Lyft", "yellow": "Taxi amarillo", "green": "Taxi verde"}
TODA_LA_CIUDAD = "Toda la ciudad"
MIN_VIAJES = 1000  # grupos (borough, hora) con menos viajes se ocultan: un porcentaje con 3 viajes no dice nada


def leer(api, pregunta):
    """(título, DataFrame) de GET {api}/resultados/{pregunta}."""
    with urllib.request.urlopen(f"{api.rstrip('/')}/resultados/{pregunta}", timeout=30) as r:
        datos = json.load(r)
    return datos["titulo"], pd.DataFrame(datos["filas"], columns=datos["columnas"])


def _fecha(df):
    return pd.to_datetime(df["year"] + "-" + df["month"] + "-01")


def _nombre(df):
    return df.assign(nombre=df["compania"].map(NOMBRES))


# ------------------------------------------------------------------ P1
def p1_participacion(df, borough=TODA_LA_CIUDAD):
    """Participación (%) de cada compañía por mes, en un borough o en toda la ciudad."""
    if borough != TODA_LA_CIUDAD:
        df = df[df["borough"] == borough]
    g = df.groupby(["year", "month", "compania"], as_index=False)["viajes"].sum()
    g["participacion"] = 100 * g["viajes"] / g.groupby(["year", "month"])["viajes"].transform("sum")
    return _nombre(g.assign(fecha=_fecha(g)))


def p1_por_anio(df, borough=TODA_LA_CIUDAD):
    """Participación (%) de cada compañía en 2024 y en 2025."""
    g = p1_participacion(df, borough).groupby(["year", "compania"], as_index=False)["viajes"].sum()
    g["participacion"] = 100 * g["viajes"] / g.groupby("year")["viajes"].transform("sum")
    return g.pivot(index="compania", columns="year", values="participacion")


# ------------------------------------------------------------------ P2
def p2_costo(df, por, borough=TODA_LA_CIUDAD):
    """Costo por milla (USD) agrupado por `por` (lista de columnas), como razón de sumas."""
    if borough != TODA_LA_CIUDAD:
        df = df[df["borough"] == borough]
    df = df.assign(tarifa=df["costo_por_milla"] * df["millas"])
    g = df.groupby(por, as_index=False)[["tarifa", "millas", "viajes"]].sum()
    return _nombre(g.assign(costo_por_milla=g["tarifa"] / g["millas"]))


# ------------------------------------------------------------------ P3
def p3_por_hora(df, borough):
    """% que recibe el conductor por hora en un borough (filas exactas del resultado)."""
    g = df[(df["borough"] == borough) & (df["viajes"] >= MIN_VIAJES)]
    return _nombre(g.rename(columns={"pct_conductor": "pct"}))


# ------------------------------------------------------------------ P4
def p4_espera(df, por, borough=TODA_LA_CIUDAD):
    """Espera promedio (min) y % de esperas de más de 10 min, ponderados por viajes."""
    if borough != TODA_LA_CIUDAD:
        df = df[df["borough"] == borough]
    df = df.assign(min_x=df["espera_promedio_min"] * df["viajes"], pct_x=df["pct_mas_10_min"] * df["viajes"])
    g = df.groupby(por, as_index=False)[["min_x", "pct_x", "viajes"]].sum()
    g = g.assign(espera_min=g["min_x"] / g["viajes"], pct_mas_10=g["pct_x"] / g["viajes"])
    return _nombre(g[g["viajes"] >= MIN_VIAJES])


# ------------------------------------------------------------------ P5
def p5_dimension(df, dimension):
    return df[df["dimension"] == dimension].copy()


def p5_zonas(df, n=8, min_viajes=20000):
    """Las n zonas de origen con propina más alta y las n con la más baja (solo zonas con volumen)."""
    z = p5_dimension(df, "zona_origen")
    z = z[z["viajes"] >= min_viajes].sort_values("propina_pct")
    return pd.concat([z.tail(n).assign(grupo="Más alta"), z.head(n).assign(grupo="Más baja")])


# ------------------------------------------------------------------ P6
def p6_mensual(df):
    """Viajes hacia la zona de cobro por mes, 2024 frente a 2025, y la variación (%)."""
    g = df.groupby(["year", "month"], as_index=False)["viajes"].sum()
    t = g.pivot(index="month", columns="year", values="viajes").reset_index()
    return t.assign(variacion=100 * (t["2025"] / t["2024"] - 1))


def p6_companias(df):
    """Viajes por compañía en 2024 y 2025, su variación (%) y su participación en cada año."""
    t = df.groupby(["compania", "year"])["viajes"].sum().unstack("year")
    t["variacion"] = 100 * (t["2025"] / t["2024"] - 1)
    for anio in ("2024", "2025"):
        t[f"part_{anio}"] = 100 * t[anio] / t[anio].sum()
    return _nombre(t.reset_index())

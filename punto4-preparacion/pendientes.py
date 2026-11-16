"""Layout de la zona trusted y cálculo de qué falta preparar. Python puro, sin dependencias.

Lo usan el Glue job (preparar.py), la Lambda de la state machine (lambda_pendientes.py) y preparar_local.py,
así que la ejecución automática, la manual y un reintento ven exactamente lo mismo.

  trusted/{dataset}/year=YYYY/month=MM/        detalle por servicio
  trusted/taxi_zones/                          zonas, sin partición
  trusted/_control/{dataset}/{YYYY-MM}.json    control que escribe el job al terminar bien
  trusted/_control/taxi_zones.json
"""
import re

TRUSTED = "trusted/"
CONTROL = TRUSTED + "_control/"
CLAVE_ZONAS_RAW = "raw/taxi_zones/taxi_zones.parquet"
SIN_MES = "na"  # valor de --mes para taxi_zones
PARTICION_RAW = re.compile(r"raw/([^/]+)/year=(\d{4})/month=(\d{2})/[^/]+\.parquet$")  # como ingestar.py:25


def prefijo_raw(dataset, mes):
    anio, m = mes.split("-")
    return f"raw/{dataset}/year={anio}/month={m}/"


def prefijo_trusted(tabla, mes, servicio=None):
    """trusted/{tabla}/[servicio=X/]year=YYYY/month=MM/, o trusted/taxi_zones/."""
    if mes == SIN_MES:
        return f"{TRUSTED}{tabla}/"
    anio, m = mes.split("-")
    medio = f"servicio={servicio}/" if servicio else ""
    return f"{TRUSTED}{tabla}/{medio}year={anio}/month={m}/"


def clave_control(dataset, mes):
    return f"{CONTROL}taxi_zones.json" if mes == SIN_MES else f"{CONTROL}{dataset}/{mes}.json"


def dataset_mes(clave_raw):
    """(dataset, mes) de una clave de raw, o None si no es un archivo de datos."""
    if clave_raw == CLAVE_ZONAS_RAW:
        return "taxi_zones", SIN_MES
    m = PARTICION_RAW.match(clave_raw)
    return (m.group(1), f"{m.group(2)}-{m.group(3)}") if m else None


def pendientes(raw, controles, workers):
    """Pares (dataset, mes) cuyo control no existe o es más viejo que su archivo de raw.

    raw y controles: {clave: LastModified}. workers: {dataset: n}; los datasets fuera de workers se ignoran.
    Devuelve [{"dataset", "mes", "workers"}] ordenado por (dataset, mes).
    """
    resultado = []
    for clave, modificado in raw.items():
        par = dataset_mes(clave)
        if not par or par[0] not in workers:
            continue
        control = controles.get(clave_control(*par))
        if control is None or control < modificado:
            resultado.append({"dataset": par[0], "mes": par[1], "workers": workers[par[0]]})
    return sorted(resultado, key=lambda p: (p["dataset"], p["mes"]))

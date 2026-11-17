"""Test de catalogo.py sin AWS: python punto5-catalogo/test_catalogo.py -> ok"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "punto5-catalogo"), str(RAIZ / "punto4-preparacion")]

import catalogo  # noqa: E402
import contrato  # noqa: E402

TIPOS_DERIVADAS = {"pickup_date": "date", "pickup_hour": "int", "duracion_min": "double", "espera_seg": "bigint"}


def esquema(ds, mes="2024-01"):
    """Como esquema_detalle del control: contrato renombrado + derivadas + banderas."""
    cols = [[n, t] for n, t, _ in contrato.DETALLE[ds].values()]
    cols += [[d, TIPOS_DERIVADAS[d]] for d in contrato.derivadas(ds)]
    cols += [[b, "boolean"] for b in contrato.banderas(ds, mes)]
    return cols


tablas = catalogo.columnas({ds: esquema(ds) for ds in ("yellow", "green", "hvfhv", "taxi_zones")})
assert sorted(tablas) == ["green", "hvfhv", "taxi_zones", "viajes", "yellow"], sorted(tablas)
viajes = dict(tablas["viajes"])
assert list(viajes) == list(contrato.viajes("yellow")), "viajes respeta el orden del contrato"
assert viajes["compania"] == viajes["pu_borough"] == "string"
assert viajes["pickup_datetime"] == "timestamp" and viajes["pickup_hour"] == "int"
assert viajes["pu_zona_id"] == "int" and viajes["fuera_de_mes"] == "boolean"
assert all(viajes[c] == "double" for c in ("millas", "tarifa_base", "recargos", "peajes", "propina",
                                             "cbd_fee", "total_pagado"))
assert not {"servicio", "year", "month"} & set(viajes) & {n for t in tablas.values() for n, _ in t}

# Un servicio con un tipo distinto hace fallar viajes en vez de catalogar mal
malo = esquema("green")
malo[[n for n, _ in malo].index("pickup_datetime")][1] = "string"
try:
    catalogo.columnas({"yellow": esquema("yellow"), "green": malo})
    raise AssertionError("debió fallar")
except ValueError:
    pass

claves = ["trusted/_control/yellow/2024-01.json", "trusted/_control/hvfhv/2025-12.json",
          "trusted/_control/taxi_zones.json", "trusted/_control/otra-cosa.txt"]
parts = catalogo.particiones(claves)
assert parts == {"yellow": {("2024", "01")}, "hvfhv": {("2025", "12")},
                 "viajes": {("yellow", "2024", "01"), ("hvfhv", "2025", "12")}}, parts

assert catalogo.ubicacion("b", "viajes", ("green", "2024", "03")) == \
    "s3://b/trusted/viajes/servicio=green/year=2024/month=03/"
assert catalogo.ubicacion("b", "taxi_zones") == "s3://b/trusted/taxi_zones/"
assert catalogo.ubicacion("b", "yellow") == "s3://b/trusted/yellow/"
e = catalogo.entrada_tabla("b", "viajes", tablas["viajes"])
assert [k["Name"] for k in e["PartitionKeys"]] == ["servicio", "year", "month"]
assert catalogo.entrada_tabla("b", "taxi_zones", tablas["taxi_zones"])["PartitionKeys"] == []
print("ok")

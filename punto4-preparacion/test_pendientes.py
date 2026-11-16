"""Chequeo de qué falta preparar. Uso: python punto4-preparacion/test_pendientes.py"""
from datetime import datetime, timedelta

import pendientes as p

T = datetime(2026, 11, 15, 12, 0)
ANTES, DESPUES = T - timedelta(hours=1), T + timedelta(hours=1)
W = {"taxi_zones": 2, "green": 2, "yellow": 4, "hvfhv": 10}

raw = {
    "raw/green/year=2024/month=01/green_tripdata_2024-01.parquet": T,
    "raw/green/year=2024/month=02/green_tripdata_2024-02.parquet": T,
    "raw/yellow/year=2025/month=12/yellow_tripdata_2025-12.parquet": T,
    "raw/hvfhv/year=2024/month=03/fhvhv_tripdata_2024-03.parquet": T,
    "raw/taxi_zones/taxi_zones.parquet": T,
    "raw/green/year=2024/month=01/_tmp.json": T,  # no es Parquet: se ignora
    "raw/fhv/year=2024/month=01/fhv_tripdata_2024-01.parquet": T,  # fuera de workers: se ignora
}
controles = {
    "trusted/_control/green/2024-01.json": DESPUES,  # más nuevo que raw: hecho
    "trusted/_control/green/2024-02.json": ANTES,  # más viejo que raw: pendiente
    "trusted/_control/taxi_zones.json": DESPUES,
    # yellow 2025-12 y hvfhv 2024-03 sin control: pendientes
}

assert p.pendientes(raw, controles, W) == [
    {"dataset": "green", "mes": "2024-02", "workers": 2},
    {"dataset": "hvfhv", "mes": "2024-03", "workers": 10},
    {"dataset": "yellow", "mes": "2025-12", "workers": 4},
]
assert p.pendientes(raw, {}, W)[-2:] == [
    {"dataset": "taxi_zones", "mes": "na", "workers": 2},
    {"dataset": "yellow", "mes": "2025-12", "workers": 4},
]
# Mismo resultado sin importar el orden del listado (determinista)
assert p.pendientes(dict(reversed(list(raw.items()))), controles, W) == p.pendientes(raw, controles, W)
assert p.pendientes(raw, {**controles, **{p.clave_control(d, m): DESPUES for d, m in
                                          [("green", "2024-02"), ("hvfhv", "2024-03"), ("yellow", "2025-12")]}}, W) == []

assert p.clave_control("taxi_zones", "na") == "trusted/_control/taxi_zones.json"
assert p.clave_control("hvfhv", "2025-12") == "trusted/_control/hvfhv/2025-12.json"
assert p.prefijo_trusted("green", "2024-01") == "trusted/green/year=2024/month=01/"
assert p.prefijo_trusted("viajes", "2024-01", "green") == "trusted/viajes/servicio=green/year=2024/month=01/"
assert p.prefijo_trusted("taxi_zones", "na") == "trusted/taxi_zones/"
assert p.prefijo_raw("yellow", "2025-03") == "raw/yellow/year=2025/month=03/"
print("ok")

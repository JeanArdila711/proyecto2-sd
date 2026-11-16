"""Chequeo del contrato de trusted. Uso: python punto4-preparacion/test_contrato.py

Los esquemas de raw son los leídos de los footers el 2026-11-15 (research § Zona raw tal como está) y, para
green, los de punto2-fuentes/ec2/esquema.sql, con los nombres de tipo que reporta Spark.
"""
import contrato as c

TS = "timestamp_ntz"  # Spark 3.5 lee timestamp[us] sin zona como timestamp_ntz
YELLOW_2024 = [
    ("VendorID", "int"), ("tpep_pickup_datetime", TS), ("tpep_dropoff_datetime", TS), ("passenger_count", "bigint"),
    ("trip_distance", "double"), ("RatecodeID", "bigint"), ("store_and_fwd_flag", "string"),
    ("PULocationID", "int"), ("DOLocationID", "int"), ("payment_type", "bigint"), ("fare_amount", "double"),
    ("extra", "double"), ("mta_tax", "double"), ("tip_amount", "double"), ("tolls_amount", "double"),
    ("improvement_surcharge", "double"), ("total_amount", "double"), ("congestion_surcharge", "double"),
    ("Airport_fee", "double"),
]
YELLOW_2025 = YELLOW_2024 + [("cbd_congestion_fee", "double")]
GREEN = [
    ("trip_id", "bigint"), ("VendorID", "bigint"), ("lpep_pickup_datetime", TS), ("lpep_dropoff_datetime", TS),
    ("store_and_fwd_flag", "string"), ("RatecodeID", "bigint"), ("PULocationID", "bigint"),
    ("DOLocationID", "bigint"), ("passenger_count", "bigint"), ("trip_distance", "double"),
    ("fare_amount", "double"), ("extra", "double"), ("mta_tax", "double"), ("tip_amount", "double"),
    ("tolls_amount", "double"), ("ehail_fee", "double"), ("improvement_surcharge", "double"),
    ("total_amount", "double"), ("payment_type", "bigint"), ("trip_type", "bigint"),
    ("congestion_surcharge", "double"), ("cbd_congestion_fee", "double"), ("mes_archivo", "string"),
    ("cargado_en", TS),
]
HVFHV_2024 = [
    ("hvfhs_license_num", "string"), ("dispatching_base_num", "string"), ("originating_base_num", "string"),
    ("request_datetime", TS), ("on_scene_datetime", TS), ("pickup_datetime", TS), ("dropoff_datetime", TS),
    ("PULocationID", "int"), ("DOLocationID", "int"), ("trip_miles", "double"), ("trip_time", "bigint"),
    ("base_passenger_fare", "double"), ("tolls", "double"), ("bcf", "double"), ("sales_tax", "double"),
    ("congestion_surcharge", "double"), ("airport_fee", "double"), ("tips", "double"), ("driver_pay", "double"),
    ("shared_request_flag", "string"), ("shared_match_flag", "string"), ("access_a_ride_flag", "string"),
    ("wav_request_flag", "string"), ("wav_match_flag", "string"),
]
HVFHV_2025 = HVFHV_2024 + [("cbd_congestion_fee", "double")]
ZONAS = [("LocationID", "bigint"), ("Borough", "string"), ("Zone", "string"), ("service_zone", "string")]

# Los esquemas reales pasan, con y sin cbd_congestion_fee
for ds, esquema in [("yellow", YELLOW_2024), ("yellow", YELLOW_2025), ("green", GREEN), ("hvfhv", HVFHV_2024),
                    ("hvfhv", HVFHV_2025), ("taxi_zones", ZONAS)]:
    assert c.validar(ds, esquema) == [], (ds, c.validar(ds, esquema))
# También con timestamp con zona
assert c.validar("yellow", [(n, "timestamp" if t == TS else t) for n, t in YELLOW_2025]) == []

for ds, columnas in c.DETALLE.items():
    destinos = [d for d, _, _ in columnas.values()]
    assert len(destinos) == len(set(destinos)), ds
    assert all(d == d.lower() for d in destinos), ds
    agregadas = list(c.derivadas(ds)) + list(c.banderas(ds, "2024-01"))
    assert not set(agregadas) & set(destinos), ds
    if ds != "taxi_zones":
        assert {"pickup_datetime", "dropoff_datetime", "pulocationid", "dolocationid"} <= set(destinos), ds
        assert c.DISTANCIA[ds] in destinos, ds
        for componente, cols in c.TARIFA[ds].items():
            assert set(cols) <= set(destinos), (ds, componente, set(cols) - set(destinos))
# Los descartes de green no llegan a trusted
assert not c.DESCARTADAS["green"] & set(c.DETALLE["green"])

# validar() detecta lo que tiene que detectar
sin_obligatoria = [x for x in YELLOW_2024 if x[0] != "fare_amount"]
assert c.validar("yellow", sin_obligatoria) == ["falta la columna obligatoria: fare_amount"]
assert c.validar("yellow", YELLOW_2024 + [("nueva", "double")]) == ["columna desconocida: nueva (double)"]
tipo_malo = [(n, "string" if n == "trip_distance" else t) for n, t in YELLOW_2024]
assert c.validar("yellow", tipo_malo) == ["tipo incompatible: trip_distance es string, el contrato pide double"]
assert c.validar("green", [x for x in GREEN if x[0] != "cbd_congestion_fee"]) == []  # no obligatoria

assert c.familia("decimal(10,2)") == "decimal" and c.familia("bigint") == c.familia("int") == "entero"
assert c.familia("timestamp_ntz") == c.familia("timestamp") == "tiempo"
assert c.familia("binary").startswith("otro")

# Banderas: las de HVFHV incluyen las propias; ninguna derivada queda sin definir antes de usarse
assert set(c.banderas("hvfhv", "2025-12")) - set(c.banderas("yellow", "2025-12")) == {"espera_negativa",
                                                                                      "pago_mayor_a_tarifa"}
assert "'2025-12'" in c.banderas("green", "2025-12")["fuera_de_mes"]
assert "espera_seg" in c.derivadas("hvfhv") and "espera_seg" not in c.derivadas("yellow")
assert c.derivadas("taxi_zones") == {} and c.banderas("taxi_zones", "na") == {}

# viajes: mismas columnas y en el mismo orden en los tres servicios
import re  # noqa: E402

columnas_viajes = list(c.viajes("yellow"))
assert all(list(c.viajes(s)) == columnas_viajes for s in c.SERVICIOS)
assert not {"servicio", "year", "month"} & set(columnas_viajes)  # salen de la ruta
assert set(c.BANDERAS_COMUNES) <= set(columnas_viajes)
NO_COLUMNAS = {"coalesce", "case", "when", "then", "else", "end", "d"}
for s in c.SERVICIOS:
    # Cada columna sale de algo que existe en el servicio: detalle, derivadas, banderas o el join de zonas
    disponibles = ({d for d, _, _ in c.DETALLE[s].values()} | set(c.derivadas(s)) | set(c.banderas(s, "2024-01"))
                   | {f"{lado}_{n}" for lado in ("pu", "do") for n in c.ZONA})
    for nombre, expr in c.viajes(s).items():
        sin_literales = re.sub(r"'[^']*'", "", expr)
        usadas = set(re.findall(r"[a-z_][a-z0-9_]*", sin_literales.lower())) - NO_COLUMNAS
        assert usadas <= disponibles, (s, nombre, usadas - disponibles)
    # Ninguna columna de tarifa cae en dos componentes
    todas = [col for cols in c.TARIFA[s].values() for col in cols]
    assert len(todas) == len(set(todas)), s
assert "HV0003" in c.viajes("hvfhv")["compania"] and c.viajes("green")["compania"] == "'green'"
assert c.viajes("yellow")["total_pagado"] == "total_amount"
assert c.viajes("hvfhv")["total_pagado"].count("coalesce(") == 8  # los cuatro componentes de HVFHV
print("ok")

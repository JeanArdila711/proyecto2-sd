"""Contrato de la zona trusted: esquema canónico por dataset, componentes de tarifa, derivadas y banderas.

Python puro, sin Spark: lo importan el Glue job (preparar.py) y el test (test_contrato.py).
Las derivadas y las banderas son expresiones Spark SQL que preparar.py aplica con F.expr.
"""

# Columna de raw -> (nombre en trusted, tipo Spark destino, obligatoria).
# Las no obligatorias que faltan en un archivo (cbd_congestion_fee en 2024) se agregan como NULL.
DETALLE = {
    "yellow": {
        "VendorID": ("vendorid", "int", True),
        "tpep_pickup_datetime": ("pickup_datetime", "timestamp", True),
        "tpep_dropoff_datetime": ("dropoff_datetime", "timestamp", True),
        "passenger_count": ("passenger_count", "int", True),
        "trip_distance": ("trip_distance", "double", True),
        "RatecodeID": ("ratecodeid", "int", True),
        "store_and_fwd_flag": ("store_and_fwd_flag", "string", True),
        "PULocationID": ("pulocationid", "int", True),
        "DOLocationID": ("dolocationid", "int", True),
        "payment_type": ("payment_type", "int", True),
        "fare_amount": ("fare_amount", "double", True),
        "extra": ("extra", "double", True),
        "mta_tax": ("mta_tax", "double", True),
        "tip_amount": ("tip_amount", "double", True),
        "tolls_amount": ("tolls_amount", "double", True),
        "improvement_surcharge": ("improvement_surcharge", "double", True),
        "total_amount": ("total_amount", "double", True),
        "congestion_surcharge": ("congestion_surcharge", "double", True),
        "Airport_fee": ("airport_fee", "double", True),
        "cbd_congestion_fee": ("cbd_congestion_fee", "double", False),
    },
    "green": {
        "VendorID": ("vendorid", "int", True),
        "lpep_pickup_datetime": ("pickup_datetime", "timestamp", True),
        "lpep_dropoff_datetime": ("dropoff_datetime", "timestamp", True),
        "store_and_fwd_flag": ("store_and_fwd_flag", "string", True),
        "RatecodeID": ("ratecodeid", "int", True),
        "PULocationID": ("pulocationid", "int", True),
        "DOLocationID": ("dolocationid", "int", True),
        "passenger_count": ("passenger_count", "int", True),
        "trip_distance": ("trip_distance", "double", True),
        "fare_amount": ("fare_amount", "double", True),
        "extra": ("extra", "double", True),
        "mta_tax": ("mta_tax", "double", True),
        "tip_amount": ("tip_amount", "double", True),
        "tolls_amount": ("tolls_amount", "double", True),
        "ehail_fee": ("ehail_fee", "double", True),
        "improvement_surcharge": ("improvement_surcharge", "double", True),
        "total_amount": ("total_amount", "double", True),
        "payment_type": ("payment_type", "int", True),
        "trip_type": ("trip_type", "int", True),
        "congestion_surcharge": ("congestion_surcharge", "double", True),
        "cbd_congestion_fee": ("cbd_congestion_fee", "double", False),
    },
    "hvfhv": {
        "hvfhs_license_num": ("hvfhs_license_num", "string", True),
        "dispatching_base_num": ("dispatching_base_num", "string", True),
        "originating_base_num": ("originating_base_num", "string", True),
        "request_datetime": ("request_datetime", "timestamp", True),
        "on_scene_datetime": ("on_scene_datetime", "timestamp", True),
        "pickup_datetime": ("pickup_datetime", "timestamp", True),
        "dropoff_datetime": ("dropoff_datetime", "timestamp", True),
        "PULocationID": ("pulocationid", "int", True),
        "DOLocationID": ("dolocationid", "int", True),
        "trip_miles": ("trip_miles", "double", True),
        "trip_time": ("trip_time", "bigint", True),
        "base_passenger_fare": ("base_passenger_fare", "double", True),
        "tolls": ("tolls", "double", True),
        "bcf": ("bcf", "double", True),
        "sales_tax": ("sales_tax", "double", True),
        "congestion_surcharge": ("congestion_surcharge", "double", True),
        "airport_fee": ("airport_fee", "double", True),
        "tips": ("tips", "double", True),
        "driver_pay": ("driver_pay", "double", True),
        "shared_request_flag": ("shared_request_flag", "string", True),
        "shared_match_flag": ("shared_match_flag", "string", True),
        "access_a_ride_flag": ("access_a_ride_flag", "string", True),
        "wav_request_flag": ("wav_request_flag", "string", True),
        "wav_match_flag": ("wav_match_flag", "string", True),
        "cbd_congestion_fee": ("cbd_congestion_fee", "double", False),
    },
    "taxi_zones": {
        "LocationID": ("locationid", "int", True),
        "Borough": ("borough", "string", True),
        "Zone": ("zone", "string", True),
        "service_zone": ("service_zone", "string", True),
    },
}

# Columnas de raw que no pasan a trusted: auditoría de la ingesta de green (research § green).
DESCARTADAS = {"green": {"trip_id", "mes_archivo", "cargado_en"}}

# Componentes de la tarifa por servicio, con los nombres de trusted. Se suman con coalesce(x, 0).
# No eligen ninguna definición de P2/P3: cada consulta arma la suya con estos componentes.
TARIFA = {
    "yellow": {
        "tarifa_base": ["fare_amount"],
        "recargos": ["extra", "mta_tax", "improvement_surcharge", "congestion_surcharge", "airport_fee",
                     "cbd_congestion_fee"],
        "peajes": ["tolls_amount"],
        "propina": ["tip_amount"],
    },
    "green": {
        "tarifa_base": ["fare_amount"],
        "recargos": ["extra", "mta_tax", "improvement_surcharge", "congestion_surcharge", "ehail_fee",
                     "cbd_congestion_fee"],
        "peajes": ["tolls_amount"],
        "propina": ["tip_amount"],
    },
    "hvfhv": {
        "tarifa_base": ["base_passenger_fare"],
        "recargos": ["bcf", "sales_tax", "congestion_surcharge", "airport_fee", "cbd_congestion_fee"],
        "peajes": ["tolls"],
        "propina": ["tips"],
    },
}

DISTANCIA = {"yellow": "trip_distance", "green": "trip_distance", "hvfhv": "trip_miles"}
ZONAS_DESCONOCIDAS = (264, 265)  # 264 "Unknown" y 265 "Outside of NYC" en el Taxi Zone Lookup

FAMILIAS = {
    "tinyint": "entero", "smallint": "entero", "int": "entero", "bigint": "entero",
    "float": "decimal", "double": "decimal",
    "string": "texto",
    "timestamp": "tiempo", "timestamp_ntz": "tiempo",
}


def familia(tipo):
    """Familia de un tipo Spark (simpleString). Un cast solo se permite dentro de la misma familia."""
    if tipo.startswith("decimal"):
        return "decimal"
    if tipo.startswith("varchar") or tipo.startswith("char"):
        return "texto"
    return FAMILIAS.get(tipo, "otro:" + tipo)


def validar(dataset, esquema_raw):
    """Errores del esquema de un archivo de raw contra el contrato. esquema_raw: [(columna, tipo Spark)]."""
    contrato = DETALLE[dataset]
    tipos = dict(esquema_raw)
    errores = []
    for col, tipo in esquema_raw:
        if col in DESCARTADAS.get(dataset, set()):
            continue
        if col not in contrato:
            errores.append(f"columna desconocida: {col} ({tipo})")
        elif familia(tipo) != familia(contrato[col][1]):
            errores.append(f"tipo incompatible: {col} es {tipo}, el contrato pide {contrato[col][1]}")
    for col, (_, _, obligatoria) in contrato.items():
        if obligatoria and col not in tipos:
            errores.append(f"falta la columna obligatoria: {col}")
    return errores


def derivadas(dataset):
    """Columnas derivadas: nombre -> expresión Spark SQL sobre los nombres de trusted, en orden."""
    if dataset == "taxi_zones":
        return {}
    d = {
        "pickup_date": "to_date(pickup_datetime)",
        "pickup_hour": "hour(pickup_datetime)",
        # 60D: double; un literal 60.0 en Spark SQL es decimal y la columna saldría decimal(27,6)
        "duracion_min": "(cast(dropoff_datetime as long) - cast(pickup_datetime as long)) / 60D",
    }
    if dataset == "hvfhv":
        d["espera_seg"] = "cast(pickup_datetime as long) - cast(request_datetime as long)"
    return d


def banderas(dataset, mes):
    """Banderas de calidad: nombre -> expresión Spark SQL. preparar.py las envuelve en coalesce(..., false)."""
    if dataset == "taxi_zones":
        return {}
    montos = sorted({c for cols in TARIFA[dataset].values() for c in cols})
    zonas = ", ".join(map(str, ZONAS_DESCONOCIDAS))
    b = {
        "fuera_de_mes": f"date_format(pickup_datetime, 'yyyy-MM') != '{mes}'",
        "duracion_invalida": "dropoff_datetime IS NULL OR pickup_datetime IS NULL OR dropoff_datetime <= pickup_datetime",
        "distancia_invalida": f"{DISTANCIA[dataset]} IS NULL OR {DISTANCIA[dataset]} <= 0",
        "monto_negativo": " OR ".join(f"{c} < 0" for c in montos),
        "zona_desconocida": f"pulocationid IN ({zonas}) OR dolocationid IN ({zonas})",
    }
    if dataset == "hvfhv":
        b["espera_negativa"] = "espera_seg < 0"
        b["pago_mayor_a_tarifa"] = "driver_pay > base_passenger_fare"
    return b


# viajes: tabla común a los tres servicios (fase 5). servicio, year y month salen de la ruta, no del Parquet.
SERVICIOS = ("yellow", "green", "hvfhv")
COMPANIA_HVFHV = {"HV0003": "uber", "HV0005": "lyft"}  # cualquier otra licencia: "otra"
# Columnas que agrega el join con taxi_zones en preparar.py, por extremo del viaje (pu_, do_)
ZONA = {"borough": "Borough", "zona": "Zone", "service_zone": "service_zone"}
BANDERAS_COMUNES = ("fuera_de_mes", "duracion_invalida", "distancia_invalida", "monto_negativo", "zona_desconocida")


def _suma(columnas):
    return " + ".join(f"coalesce({c}, 0D)" for c in columnas)


def viajes(dataset):
    """Columnas de viajes: nombre -> expresión Spark SQL sobre el detalle ya escrito más las columnas de zona."""
    t = TARIFA[dataset]
    if dataset == "hvfhv":
        casos = " ".join(f"WHEN '{lic}' THEN '{c}'" for lic, c in COMPANIA_HVFHV.items())
        compania = f"CASE hvfhs_license_num {casos} ELSE 'otra' END"
        total = _suma(c for cols in t.values() for c in cols)
    else:
        compania, total = f"'{dataset}'", "total_amount"
    v = {"compania": compania}
    v.update({c: c for c in ("pickup_datetime", "dropoff_datetime", "pickup_date", "pickup_hour", "duracion_min")})
    for lado in ("pu", "do"):
        v[f"{lado}_zona_id"] = f"{lado}locationid"
        v.update({f"{lado}_{nombre}": f"{lado}_{nombre}" for nombre in ZONA})
    v["millas"] = DISTANCIA[dataset]
    v.update({componente: _suma(cols) for componente, cols in t.items()})
    v["cbd_fee"] = "cbd_congestion_fee"  # NULL en 2024: el cobro empezó en 2025
    v["total_pagado"] = total
    v.update({b: b for b in BANDERAS_COMUNES})
    return v

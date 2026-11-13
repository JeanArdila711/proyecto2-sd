"""Layout de la zona raw del datalake (convención "Layout de la zona raw").

Única definición de las rutas de raw: la usan la Lambda (lambda_ingesta.py) y la EC2 (ec2_ingesta.py).

  raw/{dataset}/year=YYYY/month=MM/<archivo TLC>.parquet
  raw/taxi_zones/taxi_zones.parquet
"""

PREFIJO = "raw/"
CLAVE_ZONAS = PREFIJO + "taxi_zones/taxi_zones.parquet"


def clave(dataset, mes, archivo):
    """clave("green", "2024-03", "green_tripdata_2024-03.parquet") -> raw/green/year=2024/month=03/..."""
    anio, m = mes.split("-")
    return f"{PREFIJO}{dataset}/year={anio}/month={m}/{archivo}"


def meses(desde, hasta):
    """Meses YYYY-MM de desde a hasta, ambos incluidos."""
    a, m = map(int, desde.split("-"))
    fin = tuple(map(int, hasta.split("-")))
    while (a, m) <= fin:
        yield f"{a}-{m:02d}"
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)

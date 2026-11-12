"""Simulador de llegada de datos (corre en la EC2).

Libera uno o varios meses en las tres fuentes, como si los datos llegaran mes a mes:
  - RDS MariaDB: inserta en green_trips los viajes de green del mes y lo anota en cargas_green.
  - Archivos en EC2: deja yellow_tripdata_<mes>.parquet en la carpeta de yellow.
  - URL: adelanta el reloj simulado (Parameter Store) para que la ingesta del Punto 3 sepa
    hasta qué mes de HVFHV puede descargar de la TLC.

Uso:
  python simulador.py --desde 2024-01 --hasta 2024-03 [--forzar]
  python simulador.py --estado
"""
import argparse
import os
import time

import pyarrow.parquet as pq

from fuente import URL_TLC, conectar, descargar, env, ssm

COLUMNAS_GREEN = [
    "VendorID", "lpep_pickup_datetime", "lpep_dropoff_datetime", "store_and_fwd_flag", "RatecodeID",
    "PULocationID", "DOLocationID", "passenger_count", "trip_distance", "fare_amount", "extra", "mta_tax",
    "tip_amount", "tolls_amount", "ehail_fee", "improvement_surcharge", "total_amount", "payment_type",
    "trip_type", "congestion_surcharge", "cbd_congestion_fee",
]
LOTE = 5000


def meses(desde, hasta):
    a, m = map(int, desde.split("-"))
    fin = tuple(map(int, hasta.split("-")))
    while (a, m) <= fin:
        yield f"{a}-{m:02d}"
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


# ------------------------------------------------------------------ RDS: green
def liberar_green(con, mes, forzar):
    with con.cursor() as cur:
        cur.execute("SELECT filas FROM cargas_green WHERE mes = %s", (mes,))
        previo = cur.fetchone()
        if previo and not forzar:
            print(f"  RDS   green {mes}: ya estaba cargado ({previo[0]} filas)")
            return
        inicio = time.time()
        local = f"/tmp/green_tripdata_{mes}.parquet"
        descargar(f"{URL_TLC}/trip-data/green_tripdata_{mes}.parquet", local)
        tabla = pq.read_table(local)
        n = tabla.num_rows
        columnas = [
            tabla.column(c).to_pylist() if c in tabla.column_names else [None] * n for c in COLUMNAS_GREEN
        ]
        filas = [fila + (mes,) for fila in zip(*columnas)]
        os.remove(local)

        cur.execute("DELETE FROM green_trips WHERE mes_archivo = %s", (mes,))
        sql = (
            f"INSERT INTO green_trips ({', '.join(COLUMNAS_GREEN)}, mes_archivo) "
            f"VALUES ({', '.join(['%s'] * (len(COLUMNAS_GREEN) + 1))})"
        )
        for i in range(0, n, LOTE):
            cur.executemany(sql, filas[i : i + LOTE])
        cur.execute(
            "INSERT INTO cargas_green (mes, filas) VALUES (%s, %s) "
            "ON DUPLICATE KEY UPDATE filas = VALUES(filas), cargado_en = CURRENT_TIMESTAMP",
            (mes, n),
        )
    con.commit()
    print(f"  RDS   green {mes}: {n} filas insertadas en green_trips ({time.time() - inicio:.0f} s)")


# ------------------------------------------------------------------ EC2: yellow
def liberar_yellow(carpeta, mes, forzar):
    nombre = f"yellow_tripdata_{mes}.parquet"
    destino = os.path.join(carpeta, nombre)
    if os.path.exists(destino) and not forzar:
        print(f"  EC2   yellow {mes}: ya estaba en {carpeta}")
        return
    inicio = time.time()
    descargar(f"{URL_TLC}/trip-data/{nombre}", destino)
    tam = os.path.getsize(destino) / 2**20
    print(f"  EC2   yellow {mes}: {nombre} ({tam:.1f} MiB) en {carpeta} ({time.time() - inicio:.0f} s)")


# ------------------------------------------------------------------ URL: reloj simulado
def mes_simulado():
    try:
        return ssm().get_parameter(Name=env("TLC_PARAM_MES"))["Parameter"]["Value"]
    except ssm().exceptions.ParameterNotFound:
        return None


def adelantar_reloj(mes):
    actual = mes_simulado()
    if actual and actual >= mes:
        print(f"  URL   reloj simulado sigue en {actual}")
        return
    ssm().put_parameter(Name=env("TLC_PARAM_MES"), Value=mes, Type="String", Overwrite=True)
    print(f"  URL   reloj simulado: {actual or '(vacío)'} -> {mes}; HVFHV disponible hasta {mes}")


# ------------------------------------------------------------------ estado
def estado(con, carpeta):
    print("Estado de las fuentes")
    with con.cursor() as cur:
        cur.execute("SELECT COUNT(*), COUNT(DISTINCT mes_archivo) FROM green_trips")
        filas, n_meses = cur.fetchone()
        cur.execute("SELECT MIN(mes), MAX(mes) FROM cargas_green")
        lo, hi = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM taxi_zones")
        zonas = cur.fetchone()[0]
    print(f"  RDS   taxi_zones: {zonas} filas | green_trips: {filas} filas, {n_meses} meses ({lo or '-'} .. {hi or '-'})")
    archivos = sorted(f for f in os.listdir(carpeta) if f.endswith(".parquet"))
    total = sum(os.path.getsize(os.path.join(carpeta, f)) for f in archivos) / 2**30
    rango = f"{archivos[0][16:23]} .. {archivos[-1][16:23]}" if archivos else "-"
    print(f"  EC2   {carpeta}: {len(archivos)} archivos yellow, {total:.2f} GiB ({rango})")
    print(f"  URL   reloj simulado: {mes_simulado() or '(vacío)'}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--desde")
    p.add_argument("--hasta")
    p.add_argument("--forzar", action="store_true", help="vuelve a cargar meses ya liberados")
    p.add_argument("--estado", action="store_true", help="solo muestra el estado de las fuentes")
    args = p.parse_args()

    carpeta = env("TLC_CARPETA_YELLOW")
    con = conectar()
    try:
        if not args.estado:
            if not args.desde:
                p.error("falta --desde (o usa --estado)")
            hasta = args.hasta or args.desde
            for mes in meses(args.desde, hasta):
                print(f"Liberando {mes}")
                liberar_green(con, mes, args.forzar)
                liberar_yellow(carpeta, mes, args.forzar)
                adelantar_reloj(mes)
        estado(con, carpeta)
    finally:
        con.close()


if __name__ == "__main__":
    main()

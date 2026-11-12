"""Siembra de las fuentes (corre en la EC2): esquema de MariaDB, tabla taxi_zones y carpeta de yellow.

Es idempotente: las tablas se crean si no existen y las zonas se insertan o actualizan.
No carga viajes: eso lo hace simulador.py mes a mes.
"""
import csv
import io
import os
import urllib.request
from pathlib import Path

from fuente import URL_TLC, conectar, env


def aplicar_esquema(cur):
    sql = (Path(__file__).parent / "esquema.sql").read_text(encoding="utf-8")
    # Quitar comentarios (-- hasta fin de línea) antes de partir por ';': los comentarios pueden tener ';'.
    sin_comentarios = "\n".join(linea.split("--", 1)[0].rstrip() for linea in sql.splitlines())
    sentencias = [s.strip() for s in sin_comentarios.split(";") if s.strip()]
    for s in sentencias:
        cur.execute(s)
    print(f"esquema aplicado ({len(sentencias)} sentencias)")


def cargar_zonas(cur):
    with urllib.request.urlopen(f"{URL_TLC}/misc/taxi_zone_lookup.csv", timeout=60) as r:
        filas = list(csv.DictReader(io.StringIO(r.read().decode("utf-8"))))
    cur.executemany(
        "INSERT INTO taxi_zones (LocationID, Borough, Zone, service_zone) VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE Borough = VALUES(Borough), Zone = VALUES(Zone), service_zone = VALUES(service_zone)",
        [(int(f["LocationID"]), f["Borough"], f["Zone"], f["service_zone"]) for f in filas],
    )
    print(f"taxi_zones: {len(filas)} zonas cargadas desde {URL_TLC}/misc/taxi_zone_lookup.csv")


def main():
    carpeta = env("TLC_CARPETA_YELLOW")
    os.makedirs(carpeta, exist_ok=True)
    print(f"carpeta de archivos yellow: {carpeta}")

    con = conectar()
    try:
        with con.cursor() as cur:
            aplicar_esquema(cur)
            cargar_zonas(cur)
        con.commit()
        with con.cursor() as cur:
            cur.execute("SELECT VERSION()")
            print("MariaDB", cur.fetchone()[0])
            for tabla in ("taxi_zones", "green_trips", "cargas_green"):
                cur.execute(f"SELECT COUNT(*) FROM {tabla}")
                print(f"  {tabla}: {cur.fetchone()[0]} filas")
            cur.execute("SELECT Borough, COUNT(*) FROM taxi_zones GROUP BY Borough ORDER BY 2 DESC")
            print("  zonas por borough:", ", ".join(f"{b} {n}" for b, n in cur.fetchall()))
    finally:
        con.close()


if __name__ == "__main__":
    main()

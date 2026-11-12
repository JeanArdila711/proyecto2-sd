#!/usr/bin/env python3
"""Simulador de llegada de datos: libera meses en las tres fuentes del Punto 2.

Por cada mes:
  - RDS MariaDB: inserta los viajes de green del mes en green_trips.
  - EC2: deja el Parquet de yellow del mes en /data/tlc/yellow.
  - URL: adelanta el reloj simulado (/proyecto2-sd/simulacion/mes_actual en Parameter Store),
    que le dice a la ingesta del Punto 3 hasta qué mes de HVFHV descargar.

Corre ec2/simulador.py dentro de la EC2 por Session Manager (ver remoto.py).

Uso (desde la raíz del repo, después de sembrar.py):
  python punto2-fuentes/simular.py --mes 2024-01
  python punto2-fuentes/simular.py --desde 2024-01 --hasta 2025-12
  python punto2-fuentes/simular.py --estado
  python punto2-fuentes/simular.py --mes 2024-01 --forzar     # recarga un mes ya liberado
"""
import argparse
import re

from remoto import correr_en_ec2


def mes_valido(texto):
    if not re.fullmatch(r"(2024|2025)-(0[1-9]|1[0-2])", texto):
        raise argparse.ArgumentTypeError("usa YYYY-MM entre 2024-01 y 2025-12")
    return texto


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--mes", type=mes_valido, help="libera un solo mes")
    g.add_argument("--desde", type=mes_valido, help="primer mes de un rango (con --hasta)")
    g.add_argument("--estado", action="store_true", help="muestra qué hay en cada fuente, sin cambiar nada")
    p.add_argument("--hasta", type=mes_valido, help="último mes del rango")
    p.add_argument("--forzar", action="store_true", help="vuelve a cargar meses ya liberados")
    args = p.parse_args()

    if args.estado:
        argumentos = ["--estado"]
    else:
        desde = args.mes or args.desde
        hasta = args.mes or args.hasta or args.desde
        if hasta < desde:
            p.error("--hasta es anterior a --desde")
        argumentos = ["--desde", desde, "--hasta", hasta] + (["--forzar"] if args.forzar else [])
    correr_en_ec2("simulador.py", argumentos)


if __name__ == "__main__":
    main()

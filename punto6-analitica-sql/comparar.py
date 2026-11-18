#!/usr/bin/env python3
"""Compara los resultados de P1–P6 entre Athena, Hive y SparkSQL (y PySpark si existe) en s3://<bucket>/resultados/.

Lee lo que dejaron athena.py (CSV con encabezado), el step de Hive (texto separado por tabuladores, sin
encabezado, NULL como \\N) y el de SparkSQL (CSV con encabezado). Ordena las filas y compara celda por celda:
texto igual y números con una tolerancia de 0,01, una unidad en el último decimal de las columnas redondeadas
a 2 decimales. Cada motor suma millones de double en otro orden, y cuando la suma cae justo en el borde del
redondeo el último dígito cambia (en la muestra, `millas` de P2: 6215.24 en Athena y 6215.23 en Hive, en 368
de 17.984 filas, con el mismo costo por milla). Termina con código 1 si algún motor no coincide con Athena.

Uso (desde la raíz del repo):
  python punto6-analitica-sql/comparar.py
  python punto6-analitica-sql/comparar.py --con-pyspark   # agrega resultados/punto7/pyspark/ (Punto 7)
"""
import argparse
import csv
import io
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent
sys.path[:0] = [str(DIR.parent), str(DIR)]

from comun import config  # noqa: E402

import consultas  # noqa: E402

TOLERANCIA = 0.01 + 1e-9  # una unidad en el 2.º decimal; el 1e-9 absorbe el error de la resta en double


def leer(s3, bucket, prefijo, separador, encabezado):
    """Filas de todos los archivos bajo un prefijo (Hive y Spark parten el resultado en varios)."""
    filas, cabecera = [], None
    for pag in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefijo):
        for o in sorted(pag.get("Contents", []), key=lambda o: o["Key"]):
            nombre = o["Key"].rsplit("/", 1)[-1]
            if o["Size"] == 0 or nombre.startswith(("_", ".")) or nombre.endswith("$folder$"):
                continue
            texto = s3.get_object(Bucket=bucket, Key=o["Key"])["Body"].read().decode("utf-8")
            lector = list(csv.reader(io.StringIO(texto), delimiter=separador))
            if encabezado and lector:
                cabecera, lector = lector[0], lector[1:]
            filas += [[None if v in ("\\N", "") else v for v in f] for f in lector if f]
    return cabecera, filas


def normal(valor):
    if valor is None:
        return None
    try:
        return float(valor)
    except ValueError:
        return valor


def clave(fila):
    return [(0, "") if v is None else (1, v) if isinstance(v, float) else (2, v) for v in fila]


def iguales(a, b):
    if len(a) != len(b):
        return False
    for fa, fb in zip(a, b):
        if len(fa) != len(fb):
            return False
        for x, y in zip(fa, fb):
            if isinstance(x, float) and isinstance(y, float):
                if abs(x - y) > TOLERANCIA:
                    return False
            elif x != y:
                return False
    return True


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--con-pyspark", action="store_true")
    args = p.parse_args()
    aws = config.sesion(config.cargar())
    s3, bucket = aws.client("s3"), config.nombre_bucket(aws)
    motores = {"athena": (",", True), "hive": ("\t", False), "sparksql": (",", True)}
    if args.con_pyspark:
        motores["pyspark"] = (",", True)
    malas = 0
    print(f"{'pregunta':<9}" + "".join(f"{m:>10}" for m in motores) + "  resultado")
    for pregunta in consultas.preguntas():
        resultados = {}
        for motor, (sep, enc) in motores.items():
            prefijo = (consultas.RESULTADOS_PYSPARK if motor == "pyspark"
                       else f"{consultas.RESULTADOS}{motor}/") + f"{pregunta}/"
            _, filas = leer(s3, bucket, prefijo, sep, enc)
            resultados[motor] = sorted(([normal(v) for v in f] for f in filas), key=clave)
        base = resultados["athena"]
        # Vacío en todos: puede ser legítimo (P6 en una muestra sin 2025) y se avisa. Vacío en algunos: ese
        # motor no corrió o falló (vaciar() borra el prefijo antes de cada corrida), así que es un error.
        vacios = [m for m, r in resultados.items() if not r]
        distintos = [m for m, r in resultados.items() if m != "athena" and not iguales(base, r)]
        todos_vacios = len(vacios) == len(resultados)
        malas += bool(distintos) and not todos_vacios
        print(f"{pregunta:<9}" + "".join(f"{len(r):>10}" for r in resultados.values())
              + ("  AVISO: vacía en todos los motores" if todos_vacios
                 else f"  SIN FILAS en {', '.join(vacios)}" if vacios
                 else f"  DIFERENTE en {', '.join(distintos)}" if distintos else "  OK"))
    print("OK: los motores dan los mismos números" if not malas else f"{malas} preguntas con diferencias")
    sys.exit(1 if malas else 0)


if __name__ == "__main__":
    main()

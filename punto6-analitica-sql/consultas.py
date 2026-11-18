"""Las seis consultas del Punto 6 y su adaptación a cada motor. Python puro, sin AWS.

Cada pregunta vive en consultas/pN_*.sql, escrita una sola vez. Los tres motores aceptan el mismo SQL
salvo un detalle: el tipo texto en un CAST se llama VARCHAR en Athena (Trino) y STRING en Hive y Spark.
Los .sql lo escriben como {TEXTO} y render() lo reemplaza.
"""
from pathlib import Path

DIR = Path(__file__).resolve().parent / "consultas"
MOTORES = ("athena", "hive", "sparksql")
TEXTO = {"athena": "VARCHAR", "hive": "STRING", "sparksql": "STRING"}
RESULTADOS = "resultados/punto6/"  # s3://<bucket>/resultados/punto6/{motor}/{pregunta}...


def preguntas():
    """{'p1': Path, ...} en orden."""
    return {f.stem.split("_")[0]: f for f in sorted(DIR.glob("p*.sql"))}


def render(pregunta, motor):
    """SQL listo para el motor: sin comentarios (el CLI de Hive parte por ';', también en un comentario),
    con {TEXTO} reemplazado y sin ';' al final."""
    if motor not in MOTORES:
        raise ValueError(f"motor desconocido: {motor}")
    lineas = [l for l in preguntas()[pregunta].read_text(encoding="utf-8").splitlines()
              if not l.lstrip().startswith("--") and l.strip()]
    return "\n".join(lineas).replace("{TEXTO}", TEXTO[motor]).rstrip().rstrip(";")


def destino(bucket, motor, pregunta):
    """Carpeta (Hive, Spark) o prefijo (Athena) donde queda el resultado de una pregunta en un motor."""
    return f"s3://{bucket}/{RESULTADOS}{motor}/{pregunta}/"


def script_hive(bucket):
    """Un .q con un INSERT OVERWRITE DIRECTORY por pregunta: Hive deja cada resultado como texto
    separado por tabuladores (los nombres de zona pueden traer comas)."""
    partes = ["USE tlc_trusted;"]
    for p in preguntas():
        partes.append(f"INSERT OVERWRITE DIRECTORY '{destino(bucket, 'hive', p)}'\n"
                      "ROW FORMAT DELIMITED FIELDS TERMINATED BY '\\t'\n"
                      f"{render(p, 'hive')};")
    return "\n\n".join(partes) + "\n"

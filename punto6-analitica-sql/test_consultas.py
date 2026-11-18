#!/usr/bin/env python3
"""Chequeos de las consultas sin AWS: python punto6-analitica-sql/test_consultas.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import consultas as c  # noqa: E402

assert list(c.preguntas()) == ["p1", "p2", "p3", "p4", "p5", "p6"], c.preguntas()
for p, archivo in c.preguntas().items():
    texto = archivo.read_text(encoding="utf-8")
    assert texto.startswith(f"-- {p.upper()}."), f"{archivo.name}: el comentario de arriba nombra la pregunta"
    assert "Banderas:" in texto, f"{archivo.name}: el comentario dice qué banderas filtra"
    for motor in c.MOTORES:
        sql = c.render(p, motor)
        assert "--" not in sql and "{" not in sql and not sql.endswith(";"), (p, motor)
        assert sql.upper().startswith("SELECT"), (p, motor)
assert "AS VARCHAR" in c.render("p5", "athena") and "AS STRING" in c.render("p5", "hive")
hive = c.script_hive("b")
assert hive.count("INSERT OVERWRITE DIRECTORY") == 6
assert "'s3://b/resultados/punto6/hive/p3/'" in hive
assert all(s.strip().upper().startswith(("USE", "INSERT")) for s in hive.split(";") if s.strip())
print("ok")

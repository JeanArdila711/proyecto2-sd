"""Prueba de la app sin navegador (AppTest de Streamlit): corre las seis pestañas contra la API real y recorre
cada opción de cada selector. Falla si algo lanza una excepción. La corre desplegar.py en la EC2:
  venv/bin/python test_app.py
"""
from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=120).run()
assert not at.exception, at.exception
for radio in at.radio:
    for opcion in radio.options:
        radio.set_value(opcion).run()
        assert not at.exception, (radio.key, opcion, at.exception)
graficas = len(at.get("arrow_vega_lite_chart"))
# Con datos de un solo año (una muestra), P6 muestra un aviso en vez de sus dos gráficas
p6_sin_comparacion = any("compara 2024 con 2025" in i.value for i in at.info)
minimo = 7 if p6_sin_comparacion else 9
assert graficas >= minimo, f"se esperaban al menos {minimo} gráficas y hay {graficas}"
print(f"ok: {len(at.radio)} selectores recorridos, {graficas} gráficas, {len(at.metric)} cifras clave")

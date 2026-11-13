"""Chequeo del layout de raw. Uso: python punto3-ingesta/test_raw.py"""
import raw

assert raw.clave("green", "2024-03", "green_tripdata_2024-03.parquet") == (
    "raw/green/year=2024/month=03/green_tripdata_2024-03.parquet"
)
assert list(raw.meses("2024-11", "2025-02")) == ["2024-11", "2024-12", "2025-01", "2025-02"]
assert list(raw.meses("2024-03", "2024-03")) == ["2024-03"]
assert list(raw.meses("2024-04", "2024-03")) == []
assert len(list(raw.meses("2024-01", "2025-12"))) == 24
print("ok")

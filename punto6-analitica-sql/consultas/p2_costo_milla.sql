-- P2. ¿Cuánto cuesta la milla en taxi amarillo frente a Uber y Lyft, por zona y por hora?
-- Tabla: viajes, solo yellow y HVFHV (servicio de la partición) y compañías yellow, uber y lyft.
-- Métrica (convención "Métrica de P2"): sum(tarifa_base + recargos) / sum(millas), razón de sumas.
--   Sin peajes (dependen de la ruta) ni propina (voluntaria y en yellow solo se registra con tarjeta).
-- Banderas: NOT duracion_invalida y NOT distancia_invalida (una milla en 0 o un viaje sin duración
--   no tiene costo por milla), NOT monto_negativo (reembolsos y ajustes), NOT zona_desconocida
--   (la zona es una dimensión de la pregunta) y NOT fuera_de_mes.
-- Resultado: una fila por (compañía, zona de origen, hora del pickup) con viajes, millas y costo por milla.
SELECT compania,
       pu_zona_id AS zona_id,
       pu_borough AS borough,
       pu_zona AS zona,
       pickup_hour AS hora,
       count(*) AS viajes,
       round(sum(millas), 2) AS millas,
       round(sum(tarifa_base + recargos) / sum(millas), 4) AS costo_por_milla
FROM viajes
WHERE servicio IN ('yellow', 'hvfhv')
  AND compania IN ('yellow', 'uber', 'lyft')
  AND NOT fuera_de_mes
  AND NOT duracion_invalida
  AND NOT distancia_invalida
  AND NOT monto_negativo
  AND NOT zona_desconocida
GROUP BY compania, pu_zona_id, pu_borough, pu_zona, pickup_hour
ORDER BY compania, zona_id, hora

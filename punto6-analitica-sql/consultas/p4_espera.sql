-- P4. ¿Cuánto espera un pasajero desde que pide el viaje hasta que lo recogen, por compañía, borough y hora?
-- Tabla: hvfhv con join a taxi_zones. Espera = espera_seg (pickup_datetime - request_datetime), derivada
--   en trusted. on_scene_datetime no sirve: solo se llena en vehículos accesibles.
-- Banderas: NOT espera_negativa (pickup antes de la solicitud), NOT zona_desconocida y NOT fuera_de_mes.
-- Además se dejan fuera las esperas de más de 1 hora (espera_seg > 3600): son viajes reservados con
--   anticipación, no la espera de alguien que pide un carro en la calle, y moverían el promedio.
-- Promedios y no medianas: los percentiles son aproximados y distintos en Athena, Hive y Spark, y los
--   tres motores tienen que dar el mismo número. pct_mas_10_min da la idea de la cola.
-- Resultado: una fila por (compañía, borough de origen, hora).
SELECT CASE h.hvfhs_license_num WHEN 'HV0003' THEN 'uber' WHEN 'HV0005' THEN 'lyft' ELSE 'otra' END
           AS compania,
       z.borough,
       h.pickup_hour AS hora,
       count(*) AS viajes,
       round(avg(h.espera_seg) / 60, 4) AS espera_promedio_min,
       round(100 * avg(CASE WHEN h.espera_seg > 600 THEN CAST(1 AS DOUBLE) ELSE CAST(0 AS DOUBLE) END), 4) AS pct_mas_10_min
FROM hvfhv h
JOIN taxi_zones z ON z.locationid = h.pulocationid
WHERE NOT h.fuera_de_mes
  AND NOT h.espera_negativa
  AND NOT h.zona_desconocida
  AND h.espera_seg IS NOT NULL
  AND h.espera_seg <= 3600
GROUP BY CASE h.hvfhs_license_num WHEN 'HV0003' THEN 'uber' WHEN 'HV0005' THEN 'lyft' ELSE 'otra' END,
         z.borough, h.pickup_hour
ORDER BY compania, borough, hora

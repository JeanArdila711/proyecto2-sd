-- P6. ¿Cambió el cobro por congestión (desde el 5 de enero de 2025) la cantidad de viajes hacia la zona
--     de cobro y el reparto entre taxis y apps?
-- Tabla: viajes, 2024 y 2025.
-- Zona de cobro (convención "Zonas de cobro por congestión"): las zonas donde al menos la mitad de los
--   viajes de 2025 que empiezan y terminan en esa misma zona pagan cbd_fee > 0. No se usa la definición
--   de la MTA. Se miran los viajes internos a la zona porque el cargo se cobra también a viajes que solo
--   salen del área: con "algún viaje de 2025 hacia la zona con cargo" entraban 261 zonas (JFK, Newark,
--   casi todo Brooklyn y Queens). Con 2025 completo salen 38 zonas, todas en Manhattan, con proporciones
--   de 0,69 o más; la siguiente queda en 0,44, así que el corte en 0,5 no es sensible.
-- Banderas: NOT fuera_de_mes (comparar mes contra mes) y NOT zona_desconocida, también en la subconsulta.
-- Resultado: una fila por (año, mes, compañía) con los viajes que terminan en la zona de cobro y su
--   porcentaje dentro del mes; comparar 2025-MM contra 2024-MM responde la pregunta.
-- En una muestra sin 2025 la subconsulta no devuelve zonas y el resultado sale vacío.
SELECT year,
       month,
       compania,
       viajes,
       round(100 * CAST(viajes AS DOUBLE) / sum(viajes) OVER (PARTITION BY year, month), 4)
           AS participacion_pct
FROM (
    SELECT year, month, compania, count(*) AS viajes
    FROM viajes
    WHERE NOT fuera_de_mes
      AND NOT zona_desconocida
      AND do_zona_id IN (
          SELECT do_zona_id
          FROM viajes
          WHERE year = '2025' AND pu_zona_id = do_zona_id AND NOT fuera_de_mes AND NOT zona_desconocida
          GROUP BY do_zona_id
          -- "al menos la mitad" con enteros: avg(1.0) es DECIMAL en Athena y DOUBLE en Hive y Spark
          HAVING 2 * sum(CASE WHEN cbd_fee > 0 THEN 1 ELSE 0 END) >= count(*))
    GROUP BY year, month, compania
) t
ORDER BY year, month, compania

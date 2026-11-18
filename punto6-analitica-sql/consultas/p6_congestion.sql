-- P6. ¿Cambió el cobro por congestión (desde el 5 de enero de 2025) la cantidad de viajes hacia la zona
--     de cobro y el reparto entre taxis y apps?
-- Tabla: viajes, 2024 y 2025.
-- Zona de cobro (convención "Zonas de cobro por congestión"): las zonas de destino con algún viaje de
--   2025 con cbd_fee > 0. No se usa la definición de la MTA.
-- Banderas: NOT fuera_de_mes (comparar mes contra mes) y NOT zona_desconocida.
-- Resultado: una fila por (año, mes, compañía) con los viajes que terminan en la zona de cobro y su
--   porcentaje dentro del mes; comparar 2025-MM contra 2024-MM responde la pregunta.
-- En una muestra sin 2025 la subconsulta no devuelve zonas y el resultado sale vacío: es lo esperado.
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
      AND do_zona_id IN (SELECT DISTINCT do_zona_id FROM viajes WHERE year = '2025' AND cbd_fee > 0)
    GROUP BY year, month, compania
) t
ORDER BY year, month, compania

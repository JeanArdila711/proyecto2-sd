-- P1. ¿Cuál es la participación de mercado de taxis amarillos, verdes, Uber y Lyft por borough y por mes?
-- Tabla: viajes (los tres servicios con las mismas columnas y la zona de origen unida).
-- Banderas: NOT fuera_de_mes, para que cada viaje cuente en el mes de su archivo y no en otro.
--   Se excluyen los orígenes 264 ("Unknown") y 265 ("Outside of NYC") porque no tienen borough;
--   no se usa zona_desconocida porque también marca destinos desconocidos, y aquí solo importa el origen.
-- Resultado: una fila por (año, mes, borough de origen, compañía) con su número de viajes y su
--   porcentaje dentro del borough y el mes. Los porcentajes de un borough-mes suman 100.
SELECT year,
       month,
       pu_borough AS borough,
       compania,
       viajes,
       round(100 * CAST(viajes AS DOUBLE) / sum(viajes) OVER (PARTITION BY year, month, pu_borough), 4)
           AS participacion_pct
FROM (
    SELECT year, month, pu_borough, compania, count(*) AS viajes
    FROM viajes
    WHERE NOT fuera_de_mes
      AND pu_zona_id NOT IN (264, 265)
    GROUP BY year, month, pu_borough, compania
) t
ORDER BY year, month, borough, compania

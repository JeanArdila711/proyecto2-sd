-- P5. ¿Qué se asocia a propinas más altas en taxi amarillo: hora, distancia, zona de origen o viaje al aeropuerto?
-- Tabla: yellow (detalle; payment_type solo existe ahí) con join a taxi_zones en el origen y el destino.
-- Solo payment_type = 1 (tarjeta): las propinas en efectivo no se registran (findings.md, "Propinas").
-- Métrica: propina como porcentaje de la tarifa, sum(tip_amount) / sum(fare_amount), y la propina
--   promedio en dólares. Una sola tabla larga con una dimensión por bloque, para comparar cuánto se
--   mueve la propina con cada factor.
-- Banderas: NOT monto_negativo, NOT duracion_invalida, NOT distancia_invalida, NOT zona_desconocida
--   y NOT fuera_de_mes; además fare_amount > 0 para que el porcentaje tenga sentido.
-- Aeropuerto: tarifa de JFK o Newark (ratecodeid 2 o 3) o un extremo en una zona con
--   service_zone 'Airports' o 'EWR'.
-- {TEXTO} lo reemplaza consultas.py por el tipo texto de cada motor (VARCHAR en Athena, STRING en Hive y Spark).
SELECT dimension, valor, count(*) AS viajes,
       round(avg(tip_amount), 4) AS propina_promedio,
       round(100 * sum(tip_amount) / sum(fare_amount), 4) AS propina_pct
FROM (
    SELECT 'hora' AS dimension, lpad(CAST(y.pickup_hour AS {TEXTO}), 2, '0') AS valor,
           y.tip_amount, y.fare_amount
    FROM yellow y
    WHERE y.payment_type = 1 AND y.fare_amount > 0 AND NOT y.fuera_de_mes AND NOT y.monto_negativo
      AND NOT y.duracion_invalida AND NOT y.distancia_invalida AND NOT y.zona_desconocida
    UNION ALL
    SELECT 'distancia' AS dimension,
           CASE WHEN y.trip_distance < 1 THEN '1. menos de 1 mi'
                WHEN y.trip_distance < 3 THEN '2. 1 a 3 mi'
                WHEN y.trip_distance < 5 THEN '3. 3 a 5 mi'
                WHEN y.trip_distance < 10 THEN '4. 5 a 10 mi'
                WHEN y.trip_distance < 20 THEN '5. 10 a 20 mi'
                ELSE '6. 20 mi o más' END AS valor,
           y.tip_amount, y.fare_amount
    FROM yellow y
    WHERE y.payment_type = 1 AND y.fare_amount > 0 AND NOT y.fuera_de_mes AND NOT y.monto_negativo
      AND NOT y.duracion_invalida AND NOT y.distancia_invalida AND NOT y.zona_desconocida
    UNION ALL
    SELECT 'zona_origen' AS dimension, concat(zo.borough, ' / ', zo.zone) AS valor,
           y.tip_amount, y.fare_amount
    FROM yellow y
    JOIN taxi_zones zo ON zo.locationid = y.pulocationid
    WHERE y.payment_type = 1 AND y.fare_amount > 0 AND NOT y.fuera_de_mes AND NOT y.monto_negativo
      AND NOT y.duracion_invalida AND NOT y.distancia_invalida AND NOT y.zona_desconocida
    UNION ALL
    SELECT 'aeropuerto' AS dimension,
           CASE WHEN y.ratecodeid IN (2, 3) OR zo.service_zone IN ('Airports', 'EWR')
                     OR zd.service_zone IN ('Airports', 'EWR')
                THEN 'aeropuerto' ELSE 'no aeropuerto' END AS valor,
           y.tip_amount, y.fare_amount
    FROM yellow y
    JOIN taxi_zones zo ON zo.locationid = y.pulocationid
    JOIN taxi_zones zd ON zd.locationid = y.dolocationid
    WHERE y.payment_type = 1 AND y.fare_amount > 0 AND NOT y.fuera_de_mes AND NOT y.monto_negativo
      AND NOT y.duracion_invalida AND NOT y.distancia_invalida AND NOT y.zona_desconocida
) t
GROUP BY dimension, valor
ORDER BY dimension, valor

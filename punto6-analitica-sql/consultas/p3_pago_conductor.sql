-- P3. ¿Qué porcentaje de lo que paga el pasajero le llega al conductor en Uber y en Lyft,
--     y cómo varía por hora y borough?
-- Tabla: hvfhv (detalle; driver_pay solo existe ahí) con join a taxi_zones para el borough de origen.
-- Métrica (convención "Métrica de P3"): sum(driver_pay + tips) / sum(lo que paga el pasajero), con
--   lo que paga = base_passenger_fare + tolls + bcf + sales_tax + congestion_surcharge + airport_fee
--   + cbd_congestion_fee + tips, cada término con coalesce(x, 0).
-- Banderas: NOT monto_negativo (ajustes con montos negativos), NOT zona_desconocida (el borough es
--   una dimensión) y NOT fuera_de_mes. No se filtra pago_mayor_a_tarifa: es un caso real y por eso
--   la métrica divide por todo lo que paga el pasajero y no solo por la tarifa base.
-- Resultado: una fila por (compañía, borough de origen, hora) con viajes y porcentaje al conductor.
SELECT CASE h.hvfhs_license_num WHEN 'HV0003' THEN 'uber' WHEN 'HV0005' THEN 'lyft' ELSE 'otra' END
           AS compania,
       z.borough,
       h.pickup_hour AS hora,
       count(*) AS viajes,
       round(100 * sum(coalesce(h.driver_pay, 0) + coalesce(h.tips, 0))
             / sum(coalesce(h.base_passenger_fare, 0) + coalesce(h.tolls, 0) + coalesce(h.bcf, 0)
                   + coalesce(h.sales_tax, 0) + coalesce(h.congestion_surcharge, 0)
                   + coalesce(h.airport_fee, 0) + coalesce(h.cbd_congestion_fee, 0)
                   + coalesce(h.tips, 0)), 4) AS pct_conductor
FROM hvfhv h
JOIN taxi_zones z ON z.locationid = h.pulocationid
WHERE NOT h.fuera_de_mes
  AND NOT h.monto_negativo
  AND NOT h.zona_desconocida
GROUP BY CASE h.hvfhs_license_num WHEN 'HV0003' THEN 'uber' WHEN 'HV0005' THEN 'lyft' ELSE 'otra' END,
         z.borough, h.pickup_hour
ORDER BY compania, borough, hora

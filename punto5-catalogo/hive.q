-- Punto 5: Hive en EMR lee las tablas del Glue Data Catalog (base tlc_trusted) sin DDL propio.
-- Consultas chicas a propósito: el cluster es de un nodo. Los conteos se comparan con los controles.
USE tlc_trusted;
SHOW TABLES;
SHOW PARTITIONS green;
SELECT 'taxi_zones', count(*) FROM taxi_zones;
SELECT 'green', year, month, count(*) FROM green GROUP BY year, month ORDER BY year, month;
SELECT 'viajes green', count(*) FROM viajes WHERE servicio = 'green';
SELECT 'yellow 2025-01', count(*) FROM yellow WHERE year = '2025' AND month = '01';

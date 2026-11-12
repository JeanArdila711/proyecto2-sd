-- Esquema de la fuente RDS MariaDB (Punto 2). Lo aplica sembrar.py; es idempotente.
-- Simula la base de datos operativa de un operador de taxis verdes.

-- Las 265 zonas de taxi de la TLC (Taxi Zone Lookup).
CREATE TABLE IF NOT EXISTS taxi_zones (
    LocationID   SMALLINT UNSIGNED NOT NULL PRIMARY KEY,
    Borough      VARCHAR(32)  NOT NULL,
    Zone         VARCHAR(64)  NOT NULL,
    service_zone VARCHAR(32)  NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Viajes de taxis verdes: columnas del archivo de la TLC + columnas de auditoría
-- (trip_id, mes_archivo, cargado_en) que usa la extracción incremental del Punto 3.
CREATE TABLE IF NOT EXISTS green_trips (
    trip_id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    VendorID               INT,
    lpep_pickup_datetime   DATETIME,
    lpep_dropoff_datetime  DATETIME,
    store_and_fwd_flag     CHAR(1),
    RatecodeID             INT,
    PULocationID           SMALLINT UNSIGNED,
    DOLocationID           SMALLINT UNSIGNED,
    passenger_count        INT,
    trip_distance          DOUBLE,
    fare_amount            DOUBLE,
    extra                  DOUBLE,
    mta_tax                DOUBLE,
    tip_amount             DOUBLE,
    tolls_amount           DOUBLE,
    ehail_fee              DOUBLE,
    improvement_surcharge  DOUBLE,
    total_amount           DOUBLE,
    payment_type           INT,
    trip_type              INT,
    congestion_surcharge   DOUBLE,
    cbd_congestion_fee     DOUBLE,          -- solo existe desde 2025; NULL en 2024
    mes_archivo            CHAR(7)   NOT NULL,  -- mes del archivo TLC de origen (YYYY-MM)
    cargado_en             TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY ix_mes_archivo (mes_archivo),
    KEY ix_pickup (lpep_pickup_datetime),
    CONSTRAINT fk_green_pu FOREIGN KEY (PULocationID) REFERENCES taxi_zones (LocationID),
    CONSTRAINT fk_green_do FOREIGN KEY (DOLocationID) REFERENCES taxi_zones (LocationID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Registro de los meses que el simulador ya cargó en green_trips.
CREATE TABLE IF NOT EXISTS cargas_green (
    mes        CHAR(7)   NOT NULL PRIMARY KEY,
    filas      INT       NOT NULL,
    cargado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

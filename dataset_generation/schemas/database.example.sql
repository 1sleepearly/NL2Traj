CREATE TABLE trips (
    trip_id BIGSERIAL PRIMARY KEY,
    trip_date DATE NOT NULL,
    label BIGINT,
    trip_trajectory TGEOMPOINT NOT NULL
);

CREATE TABLE districts (
    name TEXT NOT NULL,
    adcode INTEGER,
    geometry GEOMETRY(MultiPolygon, 4326) NOT NULL
);


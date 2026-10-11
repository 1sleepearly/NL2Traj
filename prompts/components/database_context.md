# Database Context

```sql
/* Table Schemas:
CREATE TABLE trips (
    trip_id BIGSERIAL PRIMARY KEY,
    trip_date DATE NOT NULL,
    label BIGINT,
    trip_trajectory TGEOMPOINT NOT NULL
);

CREATE TABLE districts (
    name TEXT,
    adcode INTEGER,
    geometry GEOMETRY(MultiPolygon, 4326)
);
*/
```

```text
/* Spatial schema notes:
- districts.geometry is a WGS84 (SRID 4326) administrative-area MultiPolygon.
- Spatial predicates operate on geometry values. Metric distance/length calculations
  may cast derived geometry values to geography.
*/
```


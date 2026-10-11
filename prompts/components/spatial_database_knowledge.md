# Spatial-Database Knowledge

```text
/* PostGIS callable reference:
- ST_Distance(geography, geography) returns distance in meters.
- ST_DWithin(geography, geography, meters) tests a metric distance threshold.
- ST_Length(geography) returns length in meters.
- ST_Area(geography) returns area in square meters.
- ST_Centroid(geometry) returns a centroid geometry.
- ST_Intersects(geometry, geometry) returns boolean.
- ST_Touches(geometry, geometry) returns boolean.
- ST_Covers(geometry, geometry) returns boolean.
- ST_Within(geometry, geometry) returns boolean.
- ST_Intersection(geometry, geometry) returns geometry.
- ST_Point(longitude, latitude) constructs a point; ST_SetSRID(geometry, 4326)
  assigns WGS84 coordinates.
- Cast geometry to geography for metric distance, length, or radius values.
*/
```


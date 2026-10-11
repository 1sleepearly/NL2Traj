# Spatial-database knowledge

This component contains geometry-level rules. It does not describe how to clip or measure dynamic trajectory objects.

| Semantic relation | Computation objects | PostGIS-style template |
|---|---|---|
| Depart from a region | trajectory start point + region polygon | `ST_Covers(region, start_point)` |
| Arrive at a region | trajectory end point + region polygon | `ST_Covers(region, end_point)` |
| Pass through a region | complete trajectory line + region polygon | `ST_Intersects(trajectory_line, region)` |
| Fully remain within a region | complete trajectory line + region polygon | `ST_CoveredBy(trajectory_line, region)` |
| Distance between points | point + point | `ST_Distance(point_a::geography, point_b::geography)` |
| Complete path length | complete trajectory line | `ST_Length(trajectory_line::geography)` |

Use `ST_Covers` for administrative membership when boundary points should count. Use projected coordinates or `geography` for metric distance and length. Do not use geometry aggregation functions merely to select one named region; select or join the intended region row explicitly.


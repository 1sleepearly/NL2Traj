# Trajectory-processing knowledge

This component contains rules for dynamic trajectory objects and local trajectory segments.

## Complete trajectory access

- Start point: `startValue(trip_trajectory)`
- End point: `endValue(trip_trajectory)`
- Start/end time: `startTimestamp(...)`, `endTimestamp(...)`
- Duration: `duration(trip_trajectory)`
- Geometric path: `trajectory(trip_trajectory)`

## Restriction and local segments

- Restrict to a time span with `atTime(trajectory, tstzspan(...))`.
- Extract the portion inside a region with `atGeometry(trajectory, region_geometry)`.
- For a time-and-region-local metric, compose the restrictions before measurement.
- A restriction can return `NULL`; filter or handle an empty result before conversion or measurement.
- Convert a selected moving segment with `trajectory(local_segment)` when a geometric line is required.

## Local metrics

- Distance: measure the geometric line of the selected segment in metric units.
- Duration: apply `duration` to the selected moving segment.
- Average speed: divide the selected segment's distance by its duration with consistent units and a protected denominator.

Do not substitute a complete-trajectory metric for a local-segment metric. When a query ranks by a segment in one region and reports metrics for a segment in another region, construct and preserve the two computation objects independently.


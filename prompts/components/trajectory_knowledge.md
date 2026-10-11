/* General trajectory-query domain knowledge (public pilot version 2.4, frozen)

Purpose and boundary:
- This document describes reusable trajectory semantics and their composition.
- It is independent of a particular benchmark schema, place-name inventory,
  question list, expected output columns, and scoring policy.
- Database schema grounding, clock-period definitions, and output requirements
  are supplied separately.
*/

## 1. Trajectory model

- A trajectory is a moving object's position evolving over time. Distinguish
  the temporal object, its spatial trace, its temporal extent, and positions
  obtained at particular instants.
- Endpoint roles are different from path roles. Origin and destination concern
  the first and last values; visiting or passing concerns the trace between
  them.
- A restriction produces a subtrajectory. Metrics computed after restriction
  describe that subtrajectory, not the original trajectory.

### 1.1 Temporal subtype and interpolation

- A temporal value may be an Instant, InstantSet, Sequence, or SequenceSet.
  An InstantSet contains observations without an assumed evolution between
  them; a Sequence has an interpolation-defined evolution; a SequenceSet may
  contain several disjoint sequences separated by periods where the value is
  unknown.
- Linear, stepwise, and discrete interpolation imply different values between
  observations. Never infer continuous movement without respecting the stored
  interpolation. `tempSubtype()` and `interpolation()` expose these properties.
- Do not bridge gaps between components of a SequenceSet when deriving motion,
  distance, duration, visits, or speed. A bounding interval and the union of
  periods where a value is defined are different temporal extents.

## 2. Reusable semantic roles

- Origin/departure role: first position and first timestamp.
- Destination/arrival role: last position and last timestamp.
- Path/visit role: the spatial trace intersects or enters a referenced region.
- Instant-position role: the position of the moving object at a specified time.
- Temporal-subtrajectory role: movement occurring within a time interval.
- Spatial-subtrajectory role: movement occurring inside a spatial region.
- Spatiotemporal-subtrajectory role: movement satisfying both temporal and
  spatial restrictions.

Typical Chinese lexical cues include: “起点/出发/从…出发” for origin,
“终点/到达/目的地” for destination, “经过/途经/穿过” for a path visit,
and “在…期间移动” or “在…内部行驶” for temporal or spatial subtrajectories.
Lexical cues identify roles; they do not by themselves determine aggregation,
units, or output columns.

## 3. Selection versus restriction

- A cohort condition selects whole trajectories. Examples are trajectories
  whose departure time is in an interval or whose destination is in a region.
- A movement-scope condition restricts trajectories. Examples are distance
  travelled during an interval or duration spent inside a region.
- After cohort selection, a requested whole-trajectory metric remains defined
  on the original trajectory.
- After movement restriction, a requested local metric is defined on the
  resulting subtrajectory.
- Do not infer restriction merely because a question contains a time or place;
  determine whether that phrase modifies the trajectory cohort or the measured
  movement.

## 4. Composing time and space

- Temporal and spatial restrictions may be composed. Apply each restriction
  to the current temporal object and compute local metrics only afterwards.
- Restriction may yield no temporal object. Test the restricted value for
  existence before deriving a trace, duration, length, speed, or aggregate.
- When a restricted value is reused, materialize it once so every downstream
  metric has the same scope.
- Restriction order should reflect the stated scope. For the intersection of a
  time interval and region, both restrictions must be represented; neither a
  departure-time filter nor a whole-path intersection is an equivalent metric
  scope.

## 5. Spatial relations

- Point membership, path intersection, complete containment, and boundary
  contact are different relations. Choose the relation matching the requested
  role rather than substituting one for another.
- A path visiting a region does not imply that its origin or destination lies
  there, and endpoint membership does not imply that the path remains there.
- Metric distance and length require an appropriate metric coordinate model;
  longitude/latitude geometry should not be treated as planar meters.
- Straight-line endpoint distance and travelled path length measure different
  properties and should remain distinct.
- Boundary contact, entry into the interior, containment, and crossing are
  distinct events. A generic intersection includes boundary contact; use a
  stricter relation only when the requested semantics require interior entry.
- Spatial restriction of a temporal geometric point is evaluated spatially in
  2D. Z coordinates do not by themselves change region membership.

### 5.1 Region-transition terminology

- Keep three concepts separate: an inter-region/OD trip has origin and
  destination assigned to different regions; a multi-region path visits more
  than one region; a boundary-crossing event is a time-local transition between
  region memberships. They are not equivalent when a path leaves and returns,
  touches a boundary, or passes through an intermediate region.
- A trip-category phrase such as “inter-region/cross-district trip” without an
  explicit path qualifier normally denotes different origin and destination
  regions in origin-destination analysis. Wording that explicitly mentions the
  path, regions visited, or a number of regions denotes path-region relations
  instead. If the application defines the term differently, its domain lexicon
  takes precedence.
- To compare endpoint regions, bind each endpoint to its actual containing
  region identifier and compare identifiers. Testing that an endpoint is not
  in one chosen region does not establish its actual region.

## 6. Time relations

- Departure and arrival intervals refer to endpoint timestamps.
- Activity at an instant requires that the instant belong to the temporal
  extent; a position at that instant can then be obtained from the trajectory.
- Movement during an interval requires a temporal restriction before measuring
  distance, duration, speed, or spatial behavior in that interval.
- Use explicit interval-bound semantics. Adjacent intervals should not double
  count a boundary instant unless the task explicitly requires it.

### 6.1 MobilityDB time types and literal construction

- MobilityDB temporal restriction accepts its own `times` types, including
  `tstzspan`; PostgreSQL `tstzrange` is a different type and is not a valid
  substitute for `atTime(temporal, times)`.
- Construct a timestamp span from a textual span literal, for example
  `tstzspan('[2020-01-01 07:00:00+08, 2020-01-01 09:00:00+08)')`.
  The opening and closing bracket characters are part of the literal and
  declare inclusive or exclusive bounds.
- A conventional clock interval uses a left-closed, right-open span `[a, b)`
  when adjacent periods must not overlap. An instant-membership test may use a
  closed singleton span `[t, t]` or `valueAtTimestamp(..., TIMESTAMPTZ t)` as
  appropriate to the requested operation.
- `temporal && tstzspan(...)` is an overlap predicate and can cheaply reject
  non-overlapping objects before `atTime()` materializes a subtrajectory.
- `timeSpan(temporal)` returns the temporal object's bounding `tstzspan`.
  `startTimestamp()` and `endTimestamp()` return scalar `timestamptz` values;
  do not pass a PostgreSQL range constructed from those scalars to `atTime()`.

## 7. Metrics and units

- Duration is derived from temporal extent. Path length is derived from the
  spatial trace. Speed combines a distance and duration defined on the same
  trajectory scope.
- Guard undefined metrics, including empty restrictions and zero-duration
  divisions.
- Convert units only after establishing the underlying metric. Keep meters,
  seconds, kilometers, hours, ratios, and percentages semantically distinct.
- A ratio must state its numerator population, denominator population, and
  counting grain. Percentage scaling is a presentation decision, not a
  trajectory operation.
- Resolve ratio scope compositionally. First identify the reference population
  introduced by phrases such as “among/of trajectories satisfying P” or by a
  shared leading qualifier P; then treat an additional condition Q introduced
  as a subset (“among them”, “but”, “also”, or an equivalent construction).
  The corresponding ratio is `count(P AND Q) / count(P)`, not automatically
  `count(P AND Q) / count(all trajectories)`. Use the full collection only
  when the language explicitly names or clearly implies it as the reference.
- Numerator and denominator must use the same object identity and duplicate
  policy. Compute both from explicitly named populations rather than relying
  on row counts after different joins.
- For a disconnected temporal result, distinguish active duration (the sum of
  defined component durations) from bounding duration (last time minus first
  time). Gaps are neither movement nor dwell time unless explicitly modeled.
- Arithmetic mean of object speeds, time-weighted mean of instantaneous speed,
  and total distance divided by total active duration are different measures.
  Select one from the requested population and weighting semantics.

## 8. Aggregation grain

- Separate per-trajectory computation from collection aggregation. First
  compute an object-level metric when the question refers to the distribution
  or average of trajectory metrics.
- A ratio of summed quantities is a weighted aggregate and is not generally
  equal to the arithmetic mean of per-trajectory ratios or speeds.
- Spatial joins and restriction expansion may produce several rows per
  trajectory. Restore the requested object or group grain before counting or
  ranking.
- Ranking requires a declared group, metric direction, tie policy, and stable
  ordering when one deterministic result is expected.

## 9. Visits and ordered events

- Multiple required visits are conjunctions over the same trajectory, not
  independent result rows.
- Ordered visits require comparable temporal evidence for each visit and an
  ordering constraint between those events. Spatial intersection alone proves
  occurrence, not order.
- Repeated entries can create several valid visit events. Do not assume that
  first entry into every region captures the requested sequence unless that
  interpretation is explicitly adopted.

### 9.1 Event extraction and efficient ordering

- A spatial visit event can be represented by the non-null restricted temporal
  object `atGeometry(trajectory_object, region_geometry)`. Its temporal extent
  retains when the object was inside the region.
- When first-entry semantics are requested or explicitly adopted,
  `startTimestamp(atGeometry(...))` is the first visit time. For last-exit
  semantics, use the corresponding end timestamp. Always test the restricted
  object for non-nullness before reading an endpoint timestamp.
- For visits to several regions, compute each region-restricted temporal object
  once from the same original trajectory, materialize those values together,
  and then compare their event timestamps. This preserves a common trajectory
  grain and avoids repeated spatial restriction in predicates.
- Do not recursively call `atTime()` with a PostgreSQL range merely to express
  that one visit follows another. Event order is normally a comparison between
  scalar `timestamptz` event times. Recursive restriction is needed only when
  the intended semantics require searching among repeated visits after a prior
  event, in which case the event model and bound semantics must be stated.
- Apply cheap cohort and overlap predicates before expensive spatial
  restrictions when they are semantically available. Avoid recomputing the
  same `atGeometry()` or spatial intersection in multiple clauses.

### 9.2 Repeated visits and event quantifiers

- A non-null spatial restriction proves at least one visit. Its first timestamp
  means first entry and its last timestamp means last exit across the restricted
  value; their difference is not cumulative dwell time when visits are disjoint.
- Visit count, first visit, last visit, cumulative dwell, longest dwell, and
  re-entry are different queries. Re-entry requires evidence of multiple
  disjoint visit components, not merely a long restricted temporal extent.
- Distinguish existential order (some A event precedes some B event), first-entry
  order, and complete visit-sequence order. State which event quantifier is
  being used before comparing timestamps.

## 10. Time-varying spatial relations and proximity

- “At time t”, “ever”, “always”, and “during which periods” have different
  result semantics: a scalar position/relation, an existential Boolean, a
  universal Boolean, and a temporal Boolean or restricted time set.
- Distance at an instant, minimum distance ever, the instant of nearest
  approach, and a time-varying distance are distinct trajectory questions.
- `nearestApproachInstant()` represents the first instant attaining the minimum
  distance. Possible/ever relations answer whether a relation holds at least
  once; temporal spatial relations such as `tintersects` or `tdwithin` preserve
  how the relation evolves over time.
- When comparing two moving objects, define their common temporal support.
  Do not compare positions across intervals where either object is undefined.

## 11. MobilityDB grounding

- `startValue(tpoint)` / `endValue(tpoint)` ground endpoint positions.
- `startTimestamp(temporal)` / `endTimestamp(temporal)` ground endpoint times.
- `trajectory(tpoint)` grounds the spatial trace.
- `valueAtTimestamp(temporal, timestamptz)` grounds an instant value.
- `atTime(temporal, times)` grounds temporal restriction.
- `atGeometry(tgeompoint, geometry)` grounds spatial restriction.
- `duration(temporal)` grounds elapsed duration; restriction and null checks
  must precede it when the requested scope is local.
- PostGIS predicates and metric functions operate on derived spatial values;
  select point membership, path intersection, containment, distance, or length
  according to the semantic role established above.

## 12. Observation and data-quality assumptions

- A stored trajectory is an observation model, not necessarily the exact path.
  Sampling rate, interpolation, GPS noise, and map matching affect inferred
  length, speed, boundary crossings, and visit events.
- Linear interpolation may create a spatial crossing between observations that
  was not physically travelled. Near a boundary, noise may create short false
  entries and exits. Do not silently introduce smoothing, dwell thresholds, or
  map matching unless the task or data policy specifies them.
- Preserve SRID consistency. Planar geometry units, geodetic distance, and
  network distance are different measurement models.

These mappings are primitives. A query should be constructed compositionally
from roles, scope, metric, and aggregation grain rather than selected from a
catalog of benchmark question templates.

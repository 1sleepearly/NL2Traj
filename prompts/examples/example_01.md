# Example 01: origin-destination filtering

## Question

查找在指定日期从区域 A 出发并到达区域 B 的轨迹编号。

## Logic-masked question

查找在 `<DATE>` 从 `<REGION_1>` 出发并到达 `<REGION_2>` 的轨迹编号。

## Trajectory semantics

- date filter;
- origin-region constraint on the start point;
- destination-region constraint on the end point;
- output grain: one row per trajectory.

## SQL structure

Join the two named region rows, apply origin and destination containment to the start and end points, and return distinct trajectory identifiers.


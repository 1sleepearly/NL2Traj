# Example 02: local trajectory measurement

## Question

统计指定时段内每条轨迹在区域 A 内的行驶距离。

## Logic-masked question

统计 `<TIME_RANGE>` 内每条轨迹在 `<REGION>` 内的行驶距离。

## Trajectory semantics

- restrict the moving trajectory to the requested time span;
- extract the local segment inside the region;
- measure the selected local segment, not the complete trajectory;
- output grain: one row per qualifying trajectory.

## SQL structure

Construct the requested time span, apply temporal and spatial restriction, remove empty local segments, convert each local segment to a geometric line, and calculate its metric length.


# Trajectory-semantic interpretation

- **Departure/origin** applies to the start point of a complete trajectory.
- **Arrival/destination** applies to the end point of a complete trajectory.
- **Pass through** normally applies to the geometric path of the complete trajectory, unless the question explicitly asks for a temporally restricted path.
- **Fully remain within** is stronger than intersection or passing-through.
- **During a time window** may require restricting the moving trajectory to that window before measuring distance, duration, or speed.
- **Inside a region** modifies the computation object when a metric is requested: extract the local trajectory segment inside the region before calculating the local metric.
- A single question may filter trajectories using complete-path conditions but measure different local segments. Record the computation object for every requested output separately.
- Natural-language time ranges are interpreted as left-closed and right-open unless explicitly stated otherwise.


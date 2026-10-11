# Trajectory-semantic SQL completion

## Inputs

- `{{QUESTION}}`
- `{{QUERY_SKELETON}}`
- `{{SCHEMA_MAPPING}}`
- `{{SPATIAL_DATABASE_KNOWLEDGE}}`
- `{{TRAJECTORY_KNOWLEDGE}}`

## Prompt

Complete the supplied query skeleton as executable PostgreSQL SQL for a PostGIS/MobilityDB trajectory database.

Use spatial-database knowledge for geometry-level relations and measurements. Use trajectory knowledge for time restriction, spatial clipping, local-segment extraction, conversion, and movement metrics. Preserve the computation object assigned to every constraint and requested value in the skeleton.

In particular:

- do not calculate a local-segment metric on the complete trajectory;
- do not replace departure, arrival, and passing-through with one another;
- compose trajectory operators in the order required by the question;
- protect nullable clipping results and unsafe denominators where needed;
- preserve requested columns, units, grouping, ordering, and tie behavior;
- use only objects present in the supplied schema mapping.

Return executable candidate SQL without prose.

Question:
`{{QUESTION}}`

Query skeleton:
`{{QUERY_SKELETON}}`

Schema mapping:
`{{SCHEMA_MAPPING}}`

Spatial-database knowledge:
`{{SPATIAL_DATABASE_KNOWLEDGE}}`

Trajectory knowledge:
`{{TRAJECTORY_KNOWLEDGE}}`


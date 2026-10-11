# DDL-based schema mapping

1. Use only tables, fields, types, keys, and relationships present in `{{DATABASE_DDL}}`.
2. Identify ordinary attributes, geometry columns, and moving-trajectory columns separately.
3. Map origin, destination, complete-path, temporal-window, and local-segment semantics to their intended database objects before choosing functions.
4. Use primary/foreign-key relationships or explicit spatial relationships to determine join paths.
5. Preserve the requested result grain. Spatial joins must not silently multiply trajectory records.
6. Do not invent convenient redundant fields such as precomputed start points, end points, durations, or vehicle identifiers unless they are present in the DDL.


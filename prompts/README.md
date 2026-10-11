# NL2Traj experimental prompts

This directory contains selected public prompt components used by NL2Traj during experiments. It is organized by the method described in the paper, not merely by file type.

## Method correspondence

| Directory | NL2Traj method component |
|---|---|
| `query_skeleton_generation/` | Query semantic parsing, DDL-based schema mapping, and trajectory query skeleton generation |
| `examples/` | Public examples used as structure-aware in-context references |
| `sql_completion/` | Knowledge-constrained completion of the query skeleton |
| `sql_refinement/` | Targeted correction using database and trajectory-semantic feedback |

The SQL-completion knowledge is deliberately split into:

- **spatial-database knowledge**: geometry-level predicates and measurements;
- **trajectory knowledge**: operations over dynamic trajectories and local segments.

## Assembly

```text
Question + DDL + retrieved examples
    -> query-skeleton generation

Query skeleton + schema mapping
    + spatial-database knowledge
    + trajectory knowledge
    -> trajectory-semantic SQL completion

Candidate SQL + execution/semantic feedback
    -> targeted SQL refinement
```

Placeholders such as `{{QUESTION}}` and `{{DATABASE_DDL}}` are supplied dynamically by experiment code. These files are selected public materials and do not claim to reproduce every internal prompt variant or experimental configuration.


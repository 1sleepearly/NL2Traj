# Trajectory query skeleton generation

## Inputs

- `{{QUESTION}}`: natural-language trajectory query;
- `{{DATABASE_DDL}}`: native database DDL;
- `{{RETRIEVED_EXAMPLES}}`: structurally similar examples selected after logical masking;
- `{{TRAJECTORY_SEMANTICS}}`: semantic interpretation rules;
- `{{SCHEMA_MAPPING_RULES}}`: constraints for grounding semantics to database elements.

## Prompt

You are planning an executable SQL query over a structured trajectory database.

Parse the question into explicit trajectory constraints and align every constraint with elements present in the supplied DDL. Distinguish complete-trajectory conditions from operations that require a local trajectory segment. Use the retrieved examples only as structural references; do not copy their entities, constants, or answers.

Produce a query skeleton that fixes:

1. required tables, fields, and join paths;
2. temporal, spatial, and attribute filters;
3. aggregation, grouping, ordering, and result grain;
4. the computation object for every condition and measurement;
5. placeholders for trajectory-specific operators that will be instantiated during SQL completion.

Do not invent tables or fields. Do not silently add filters absent from the question.

Question:

```text
{{QUESTION}}
```

Database DDL:

```sql
{{DATABASE_DDL}}
```

Trajectory semantics:

```text
{{TRAJECTORY_SEMANTICS}}
```

Schema-mapping rules:

```text
{{SCHEMA_MAPPING_RULES}}
```

Retrieved structural examples:

```text
{{RETRIEVED_EXAMPLES}}
```


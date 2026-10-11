# Execution-feedback SQL refinement

## Inputs

- `{{QUESTION}}`, `{{DATABASE_DDL}}`, and `{{QUERY_SKELETON}}`;
- `{{PREVIOUS_SQL}}`;
- `{{EXECUTION_FEEDBACK}}` and `{{TRAJECTORY_SEMANTIC_FEEDBACK}}`;
- the public spatial-database and trajectory knowledge components.

## Prompt

Repair the supplied SQL using the detected execution or trajectory-semantic problem. Preserve the valid query structure and previously established semantics. Modify only the portion necessary to resolve the feedback.

Execution feedback may identify an invalid field, incorrect function, argument-type mismatch, timeout-prone construction, or SQL syntax error. Trajectory-semantic feedback may identify a wrong computation object, such as measuring a complete trajectory where the question requires a local segment.

After repair, verify that every condition and output still uses the computation object assigned in the query skeleton. Return only the refined executable SQL.

Previous SQL:
```sql
{{PREVIOUS_SQL}}
```

Execution feedback:
`{{EXECUTION_FEEDBACK}}`

Trajectory-semantic feedback:
`{{TRAJECTORY_SEMANTIC_FEEDBACK}}`


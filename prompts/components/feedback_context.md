# Typed Execution and Semantic Feedback

Feedback is absent from the initial generation prompt. When a candidate fails execution or semantic validation, the formal experiment inserts the following runtime block into the otherwise unchanged NL2Traj prompt:

The exact deterministic implementation is published in [`error_diagnostics.py`](../support/error_diagnostics.py) and [`semantic_validator.py`](../support/semantic_validator.py).

```text
/* Typed trajectory feedback */
Structured correction request:
- error_type: {{ERROR_TYPE}}
- diagnosis: {{DIAGNOSIS}}
- repair_scope: {{REPAIR_SCOPE}}
- instruction: Preserve correct clauses and change only what is needed. Return exactly one corrected read-only SELECT/WITH query.
Observed detail: {{OBSERVED_DETAIL}}
Previous SQL:
{{PREVIOUS_SQL}}
```

`Observed detail` is omitted when no detail is available. For semantic failures it contains one or more validator messages in this exact shape:

```text
[{{VALIDATION_CODE}}] {{VALIDATION_MESSAGE}}
```

## Execution-error diagnoses

| `error_type` | `diagnosis` | `repair_scope` | Trigger |
| --- | --- | --- | --- |
| `schema_mismatch` | `A referenced table, column, or function is unavailable or has the wrong signature.` | `schema/operator reference` | Missing table, column, function, or matching function signature |
| `sql_syntax` | `The generated SQL is not syntactically valid.` | `syntax, aliases, or CTE structure` | Syntax, unterminated, mismatched, or “at or near” errors |
| `type_mismatch` | `An expression uses incompatible PostgreSQL/PostGIS/MobilityDB types.` | `the failing expression and its casts` | Cast, input-syntax, operator, datatype, or missing-type errors |
| `query_timeout` | `The query exceeded the execution budget.` | `filter placement and query plan` | Statement cancellation or timeout |
| `arithmetic_error` | `The query does not guard a zero denominator.` | `the affected arithmetic expression` | Division by zero |
| `unsafe_or_forbidden_sql` | `The query attempted an operation outside the read-only contract.` | `replace the statement with a SELECT query` | Permission-denied or read-only-transaction errors; not retryable |
| `execution_error` | `The database rejected the generated query.` | `the clause identified by the database error` | Fallback for unmatched database errors |

## Semantic-error diagnoses

| `error_type` | `diagnosis` | `repair_scope` | Validator codes |
| --- | --- | --- | --- |
| `wrong_spatial_semantics` | `The SQL does not preserve one or more requested trajectory spatial roles.` | `spatial predicates only` | `origin_missing`, `destination_missing`, `passing_missing`, `negation_missing` |
| `wrong_trajectory_scope` | `A metric requested for a local trajectory segment is computed on the whole trajectory.` | `segment construction and the dependent metric` | `local_space_missing`, `local_time_missing` |
| `wrong_aggregation` | `The SQL aggregation or grouping does not match the requested output grain.` | `SELECT, GROUP BY, and aggregate expressions` | `aggregate_missing`, `grouping_missing` |
| `wrong_ranking` | `The requested ranking or result limit is not implemented.` | `ORDER BY and LIMIT` | `ranking_missing`, `limit_missing` |
| `semantic_mismatch` | `The SQL is executable but violates constraints inferred from the question.` | `only the clauses named by the validation issues` | Fallback for all other semantic-validation codes |

The implementation allows up to two semantic repair rounds. Each repaired candidate is executed and validated again before constrained selection.

# Public datasets

This directory contains the three experimental test sets and the shared in-context example pool in their original Excel layouts.

| File | Rows | Purpose |
| --- | ---: | --- |
| `test/test_easy.xlsx` | 40 | Easy test set |
| `test/test_middle.xlsx` | 40 | Middle test set |
| `test/test_hard.xlsx` | 40 | Hard test set |
| `examples/examples.xlsx` | 40 | Shared retrieval pool used by NL2Traj |

The `答案` column is intentionally retained as part of the workbook schema but all of its cells are blank because query results are derived from a confidential trajectory database. Questions, reference SQL, masking, evidence, and validation-status fields remain available.

The three test sets use the same shared example pool. During evaluation, exact-question, equivalent-masked-question, and equal reference-SQL-skeleton examples are excluded before Top-2 retrieval. Reference SQL is used only for exclusion and is never placed in the model prompt.

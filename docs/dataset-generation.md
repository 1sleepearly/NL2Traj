# Multi-agent construction of test and example sets

NL2Traj uses a shared construction pipeline for evaluation questions and in-context examples. The target role changes the desired distribution and overlap constraints, but not the core quality gates.

## Workflow

1. A generation role produces a natural-language question, reference SQL, semantic specification, operation chain, difficulty, task type, and output contract.
2. Deterministic checks reject exact, masked-question, and SQL-skeleton collisions.
3. An independent reviewer reconstructs the intended semantics before inspecting whether the SQL implements them.
4. A separate overlap review compares the candidate with existing test and example tasks while ignoring entity names and constants.
5. The SQL is executed with a read-only database account.
6. Result shape, size, null patterns, and other observable properties are checked.
7. Rejected candidates produce bounded feedback for another generation round.
8. Machine-validated candidates remain pending until human confirmation.

## Test sets versus examples

Test sets emphasize coverage, difficulty stratification, and discrimination between methods. In-context examples emphasize representative mappings between language and SQL structure. Examples must additionally be checked against the complete test set to reduce leakage through paraphrases, constant substitution, or matching SQL skeletons.

## Limits of automatic validation

Database execution proves only that a query can run. It does not prove that the question is unambiguous, that the SQL faithfully implements the requested trajectory semantics, or that the result is scientifically useful. Human confirmation therefore remains a required final state.


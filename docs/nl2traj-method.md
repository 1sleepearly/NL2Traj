# NL2Traj method overview

Natural-language trajectory queries combine ordinary relational structure with temporal windows, spatial roles, dynamic trajectory restrictions, and measurements over complete or local trajectory objects. SQL can execute successfully while measuring the wrong object, such as the complete path instead of the segment inside a requested region.

NL2Traj addresses this problem with three connected modules.

## 1. Deterministic semantic emphasis and structural context

The formal implementation deterministically extracts a lightweight semantic emphasis from the question. It records signals such as temporal role, origin, destination, passing-through, requested outputs, ordering, ratios, and precision. This block supports prompt emphasis, example ranking, and post-generation checks; it is not generated through a separate LLM prompt.

## 2. Trajectory-semantic SQL completion

The original question, lightweight semantic emphasis, native database DDL, and retrieved structural examples are assembled with two complementary knowledge components:

- geometry-level spatial-database rules for points, polygons, complete trajectory lines, predicates, and metric measurements;
- trajectory-level processing rules for temporal restriction, spatial clipping, local-segment extraction, conversion, duration, distance, and speed.

Keeping these components separate makes the selected computation object explicit and distinguishes general spatial reasoning from dynamic trajectory processing.

## 3. Execution-feedback SQL refinement

Candidate SQL is executed and checked against the trajectory constraints extracted from the question. Database errors and trajectory-semantic mismatches become targeted feedback. Refinement repairs the detected portion while preserving the valid skeleton and computation-object assignments.

The selected public prompt components corresponding to these modules are documented in [`../prompts/`](../prompts/).

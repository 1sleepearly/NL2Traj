# NL2Traj method overview

Natural-language trajectory queries combine ordinary relational structure with temporal windows, spatial roles, dynamic trajectory restrictions, and measurements over complete or local trajectory objects. SQL can execute successfully while measuring the wrong object, such as the complete path instead of the segment inside a requested region.

NL2Traj addresses this problem with three connected modules.

## 1. Trajectory query skeleton generation

The method parses the question into structured trajectory constraints, grounds those constraints to native database DDL, retrieves structurally similar logic-masked examples, and produces an intermediate query skeleton. The skeleton fixes tables, fields, joins, filters, aggregation, result grain, and placeholders for trajectory-specific operations.

## 2. Trajectory-semantic SQL completion

The skeleton is completed under two complementary knowledge components:

- geometry-level spatial-database rules for points, polygons, complete trajectory lines, predicates, and metric measurements;
- trajectory-level processing rules for temporal restriction, spatial clipping, local-segment extraction, conversion, duration, distance, and speed.

Keeping these components separate makes the selected computation object explicit and distinguishes general spatial reasoning from dynamic trajectory processing.

## 3. Execution-feedback SQL refinement

Candidate SQL is executed and checked against the trajectory constraints extracted from the question. Database errors and trajectory-semantic mismatches become targeted feedback. Refinement repairs the detected portion while preserving the valid skeleton and computation-object assignments.

The selected public prompt components corresponding to these modules are documented in [`../prompts/`](../prompts/).


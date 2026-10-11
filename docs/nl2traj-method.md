# NL2Traj prompt-material guide

This document explains how the files currently published in [`prompts/`](../prompts/) relate to one another. It is a repository guide, not a complete description of the private experiment runner.

## Directory summary

The `prompts/` directory publishes the selected materials that define how the NL2Traj experiment supplies knowledge and context to the model and how it constructs targeted repair feedback. It combines fixed Markdown components with deterministic Python support code because parts of the runtime prompt—semantic emphasis and typed feedback—depend on the current question, generated SQL, execution result, and validation outcome.

The directory covers two connected stages. Initial generation combines spatial knowledge, trajectory knowledge, shared conventions, database context, retrieved examples, deterministic semantic emphasis, and the SQL output contract. If a candidate fails execution or semantic validation, repair reconstructs the same prompt and inserts a typed correction request together with the previous SQL. The complete example pool and full experiment runner are outside the public scope.

```text
question + fixed prompt components + retrieved examples
  -> deterministic semantic emphasis
  -> initial SQL generation
  -> execution and semantic validation
  -> typed feedback + previous SQL when needed
  -> targeted SQL repair
```

## Prompt assembly

[`nl2traj_prompt.md`](../prompts/nl2traj_prompt.md) is the top-level assembly specification. It records the order used by the formal experiment:

1. spatial-database knowledge;
2. trajectory knowledge;
3. shared time conventions;
4. retrieved examples;
5. deterministic semantic-template emphasis;
6. database DDL and spatial schema notes;
7. typed feedback when repairing a candidate;
8. the SQL output contract and current question.

The file uses placeholders to show runtime insertion points; it is not an independently executable prompt builder.

## Fixed prompt components

The files below [`prompts/components/`](../prompts/components/) document the fixed text and runtime formats used by that assembly:

- [`spatial_database_knowledge.md`](../prompts/components/spatial_database_knowledge.md) contains the shared PostGIS callable reference.
- [`trajectory_knowledge.md`](../prompts/components/trajectory_knowledge.md) contains the frozen trajectory-domain knowledge used by NL2Traj.
- [`time_conventions.md`](../prompts/components/time_conventions.md) contains the benchmark interval, peak-period, and timezone conventions.
- [`database_context.md`](../prompts/components/database_context.md) contains the published `trips` and `districts` DDL plus neutral spatial schema notes.
- [`example_context.md`](../prompts/components/example_context.md) records the exact Q/Hint/A few-shot wrapper, `K=2`, retrieval ordering, and strict exclusion behavior. The complete example pool is not published here.
- [`semantic_template_emphasis.md`](../prompts/components/semantic_template_emphasis.md) records the runtime text format produced from a question by `light_template.py`.
- [`feedback_context.md`](../prompts/components/feedback_context.md) records the typed repair block, execution and semantic diagnosis categories, previous-SQL insertion, and repair-round policy.
- [`system_prompts.md`](../prompts/components/system_prompts.md) contains the system messages for initial generation and feedback-based repair.
- [`output_contract.md`](../prompts/components/output_contract.md) contains the final SQL-only instruction and the question placeholder.

Text inside the documented prompt code blocks preserves the formal experiment wording. Explanatory Markdown outside those blocks is repository documentation.

## Deterministic support code

Some inserted sections cannot be represented by fixed Markdown alone. [`prompts/support/`](../prompts/support/) therefore contains the exact deterministic code associated with them:

- [`light_template.py`](../prompts/support/light_template.py) extracts lightweight semantic signals, formats the semantic-emphasis block, scores template similarity for example retrieval, and checks generated SQL against those signals.
- [`semantic_validator.py`](../prompts/support/semantic_validator.py) derives validation issues from the question, SQL, and execution result. Its issue messages become the `Observed detail` portion of semantic repair feedback.
- [`error_diagnostics.py`](../prompts/support/error_diagnostics.py) classifies database errors and semantic issues and formats the structured correction request.

These files are support logic rather than standalone prompts. They are kept under `prompts/` because they determine the dynamic content inserted into the published prompt structure.

## Initial generation and repair

For initial generation, the experiment assembles the fixed knowledge and context, creates the semantic-emphasis block from the question, leaves the typed-feedback section empty, and uses the generation system prompt.

For repair, the same assembly is rebuilt. The validator or execution diagnosis supplies the structured feedback and previous SQL, and the repair system prompt is used. The public files describe prompt construction and checking, but they do not include the complete candidate-generation, voting, execution, and final-selection runner.

## Relationship to dataset generation

The root [`prompts/`](../prompts/) directory describes the NL2Traj inference method. The separate [`dataset_generation/`](../dataset_generation/) directory contains the multi-agent process for constructing test cases and in-context examples. Dataset generation may load the two public knowledge files through its configuration, but its four agent prompts are not part of the NL2Traj inference prompt.

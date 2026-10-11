# Dataset-generation module guide

This document explains the files currently published in [`dataset_generation/`](../dataset_generation/). It does not describe private benchmark data or unreleased experiment code.

## Module summary

The `dataset_generation/` directory is a public, self-contained adaptation of the multi-agent workflow used to construct NL2Traj test cases and in-context examples. It accepts a generation configuration, database schema, operator knowledge, model credentials, a read-only database connection, and an optional reference-case index. It then generates candidate question–SQL pairs, applies deterministic duplicate checks, requests independent semantic and overlap reviews, executes eligible SQL, and records the accepted cases together with a complete audit trace.

The same implementation supports both test-set and example-set construction through `dataset_kind`. The difference lies in the configured target and reference index rather than in a separate pipeline. All exported cases are machine-validated but remain pending human confirmation. The public module excludes the private benchmark contents, production credentials, and internal experiment integration.

```text
configuration + schema + knowledge + reference cases
  -> candidate generation
  -> deterministic duplicate checks
  -> semantic review
  -> overlap review
  -> read-only SQL execution and result checks
  -> cases.jsonl + trace.jsonl + manifest.json
  -> human confirmation
```

## Entry point and configuration

- [`generate.py`](../dataset_generation/generate.py) is the command-line entry point. It loads environment variables and JSON configuration, constructs the model and database adapters, runs the builder, and writes the run directory.
- [`config.example.json`](../dataset_generation/config.example.json) selects `test` or `examples`, target counts by difficulty, retry limits, model-provider prefixes, schema and knowledge files, result constraints, and the output root.
- [`../.env.example`](../.env.example) lists the model and database environment variables expected by the public adapters.
- [`schemas/database.example.sql`](../dataset_generation/schemas/database.example.sql) is the example DDL supplied to the agents. Replace it when adapting the pipeline to another database.
- [`examples/reference_cases.jsonl`](../dataset_generation/examples/reference_cases.jsonl) demonstrates the optional reference index used by duplicate and leakage checks. For example-set construction, this input should represent the test cases against which examples are checked.

The example configuration also reads operator knowledge from [`spatial_database_knowledge.md`](../prompts/components/spatial_database_knowledge.md) and [`trajectory_knowledge.md`](../prompts/components/trajectory_knowledge.md). This is the explicit connection between dataset construction and the public knowledge files under the root `prompts/` directory.

## Pipeline implementation

[`pipeline.py`](../dataset_generation/pipeline.py) contains the public construction workflow:

1. `BuildConfig` defines the run settings loaded by `generate.py`.
2. `TYPE_CATALOG` and `DIFFICULTY_RUBRIC` assign requested task types across Easy, Middle, and Hard targets.
3. `MultiAgentDatasetBuilder._generate()` sends the schema, operator knowledge, target type, exclusions, and prior rejection feedback to the generation role.
4. `OverlapIndex` performs exact-question, masked-question, and SQL-skeleton checks.
5. `_review()` invokes an independent semantic reviewer and requires agreement on question–SQL semantics, difficulty, task type, language, ambiguity, and defects.
6. `_overlap_review()` asks a separate reviewer to compare the candidate with reference and already accepted cases.
7. The candidate SQL is executed only after the preceding gates pass.
8. The public implementation deterministically requires a JSON row list, enforces `max_result_rows`, and rejects empty results unless `allow_empty_results` is enabled.
9. Failed validation data is returned to the next generation round. A run that cannot fill a target raises `BuildIncompleteError` but still writes its partial audit.
10. `write_run_directory()` exports accepted cases and the audit records. Every case retains `human_status: "pending"`.

## Agent prompts

The Markdown files in [`dataset_generation/prompts/`](../dataset_generation/prompts/) are system prompts used by the construction roles:

- [`generator.md`](../dataset_generation/prompts/generator.md) defines the candidate JSON fields and generation constraints.
- [`reviewer.md`](../dataset_generation/prompts/reviewer.md) defines the independent question–SQL semantic review.
- [`overlap_reviewer.md`](../dataset_generation/prompts/overlap_reviewer.md) defines structural and semantic overlap review.
- [`result_reviewer.md`](../dataset_generation/prompts/result_reviewer.md) defines an LLM-based result-audit role, but the current public `pipeline.py` does not invoke it. Current result checks are the deterministic shape, size, and empty-result checks described above.

These prompts belong to dataset construction. They are separate from [`../prompts/`](../prompts/), which publishes selected prompts used by the NL2Traj query method itself.

## External adapters

[`providers.py`](../dataset_generation/providers.py) contains two adapters:

- `ChatModel` calls an OpenAI-compatible chat-completions endpoint using the configured environment-variable prefix.
- `execute_read_only()` accepts only SQL beginning with `SELECT` or `WITH`, opens PostgreSQL with a read-only transaction and a 30-second statement timeout, and serializes returned rows as JSON.

Database-level read-only permissions are still required; the application check is not a security boundary by itself.

## Generated files

Each run creates a unique directory below the configured `output_root`:

- `cases.jsonl` contains machine-validated candidates, renamed with a `T` prefix for test cases or `E` prefix for examples;
- `trace.jsonl` records generation failures, rejected candidates, validation fields, and accepted candidates;
- `manifest.json` records the run identifier, model names, reference path, case count, failure state, and `machine_validated_pending_human_confirmation` status.

Generated run directories are not included in this repository and are not connected automatically to the NL2Traj experiment runner.

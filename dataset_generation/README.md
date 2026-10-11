# Multi-agent dataset generation

This module is the public, self-contained adaptation of the pipeline used to construct NL2Traj test cases and in-context examples. It keeps the main functional gates while excluding private data, credentials, full benchmark contents, and internal experiment wiring.

## Roles and gates

```text
Generator
  -> deterministic format and overlap checks
  -> independent semantic reviewer
  -> independent semantic-overlap reviewer
  -> read-only database execution
  -> result-shape and size checks
  -> accepted candidate pending human confirmation
```

Rejected candidates produce compact feedback for the next generation round. The public implementation does not treat any single LLM decision, or SQL executability alone, as sufficient evidence of a gold case.

Agent prompts live in [`prompts/`](prompts/) because they are part of the dataset-construction implementation. They are distinct from the root [`../prompts/`](../prompts/) directory, which contains selected NL2Traj experimental prompt components.

## Test sets and example sets

Both use the same pipeline. Set `dataset_kind` to `test` or `examples`. When constructing examples, provide the complete test-question index with `--reference` so the overlap gates can reduce example/test leakage.

## Run

From the repository root:

```bash
cp .env.example .env
python -m dataset_generation.generate \
  --config dataset_generation/config.example.json \
  --reference dataset_generation/examples/reference_cases.jsonl
```

Output is written to a uniquely named directory containing:

- `cases.jsonl`: machine-validated candidates;
- `trace.jsonl`: generation, rejection, and validation audit records;
- `manifest.json`: models, status, and run metadata.

All exported cases remain `pending` until human confirmation. Generated outputs are not connected automatically to an experiment.

## Adapting the public example

Replace `schemas/database.example.sql` with your own DDL and configure a compatible read-only database. Update the operator-knowledge paths if your backend is not PostgreSQL/PostGIS/MobilityDB. Review the difficulty catalog and output contract for your domain before producing a benchmark.

## Security

The database adapter enables a read-only transaction and accepts only statements beginning with `SELECT` or `WITH`. Use a database account that has no write privileges; application-side checks are not a substitute for database permissions.

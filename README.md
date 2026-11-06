# NL2Traj

Public resources for **NL2Traj**, a natural-language query framework for trajectory databases.

The repository contains three main parts:

1. [`dataset_generation/`](dataset_generation/) - the multi-agent pipeline used to construct and validate trajectory Text-to-SQL test cases and in-context examples. Its agent prompts are part of this module.
2. [`prompts/`](prompts/) - prompt components used by the NL2Traj method during experiments, organized according to the paper.
3. [`nl2traj/`](nl2traj/) and [`data/`](data/) - the complete NL2Traj inference implementation and the public-format experimental workbooks.

## Repository map

```text
NL2Traj/
├── dataset_generation/   Multi-agent dataset construction
├── data/                 Three test sets and the shared example pool
├── nl2traj/              Complete NL2Traj inference implementation
├── prompts/              Public NL2Traj experimental prompts
├── docs/                 Concise method documentation
└── tests/                Offline tests for public utilities
```

## Quick start: dataset generation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m dataset_generation.generate \
  --config dataset_generation/config.example.json \
  --reference dataset_generation/examples/reference_cases.jsonl
```

Generation requires an OpenAI-compatible chat-completions endpoint and a PostgreSQL database with PostGIS/MobilityDB-compatible schema and functions. Configure credentials in `.env`; never commit that file.

## Quick start: NL2Traj

The public workbooks retain their original Excel schema. Their `答案` cells are blank because the execution results come from the confidential trajectory database.

```bash
cp .env.example .env
python -m nl2traj.cli data/test/test_easy.xlsx \
  --examples data/examples/examples.xlsx \
  --provider deepseek \
  --output results/easy_predictions.jsonl
```

The implementation covers Top-2 trajectory-aware retrieval, strict example isolation, adaptive 2-to-5 candidate generation, database execution, deterministic semantic validation, result-agreement scoring, typed feedback, and at most two targeted repairs. Baseline implementations are not part of this repository.

## Documentation

- [Multi-agent dataset construction](docs/dataset-generation.md)
- [NL2Traj method overview](docs/nl2traj-method.md)
- [Experimental settings](docs/experimental-settings.md)
- [Prompt organization](prompts/README.md)
- [Public data layout](data/README.md)

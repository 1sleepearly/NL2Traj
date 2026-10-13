# NL2Traj

Public resources for **NL2Traj**, a natural-language query framework for trajectory databases.

The repository contains two main parts:

1. [`dataset_generation/`](dataset_generation/) - the multi-agent pipeline used to construct and validate trajectory Text-to-SQL test cases and in-context examples. Its agent prompts are part of this module.
2. [`prompts/`](prompts/) - prompt components used by the NL2Traj method during experiments, organized according to the paper.

## Repository map

```text
NL2Traj/
├── dataset_generation/   Multi-agent dataset construction
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

## Documentation

- [Multi-agent dataset construction](docs/dataset-generation.md)
- [NL2Traj method overview](docs/nl2traj-method.md)
- [Experimental settings](docs/experimental-settings.md)
- [Prompt organization](prompts/README.md)

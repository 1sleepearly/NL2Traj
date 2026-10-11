#!/usr/bin/env python3
"""Run the public multi-agent dataset construction pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from dataset_generation.pipeline import BuildConfig, BuildIncompleteError, MultiAgentDatasetBuilder, write_run_directory
from dataset_generation.providers import ChatModel, execute_read_only


def load_reference(path: str | None) -> list[dict]:
    if not path:
        return []
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--reference", help="JSONL used for leakage and overlap checks")
    args = parser.parse_args()
    load_dotenv()
    raw = json.loads(Path(args.config).read_text(encoding="utf-8"))
    config = BuildConfig(
        dataset_kind=raw["dataset_kind"], counts=raw["counts"], max_rounds=raw.get("max_rounds", 3),
        candidates_per_request=raw.get("candidates_per_request", 2), run_name=raw.get("run_name", "trajectory"),
        language=raw.get("language", "Chinese"), allow_empty_results=raw.get("allow_empty_results", False),
        max_result_rows=raw.get("max_result_rows", 200),
    )
    schema = Path(raw["schema_path"]).read_text(encoding="utf-8")
    knowledge = "\n\n".join(Path(path).read_text(encoding="utf-8") for path in raw["operator_knowledge_paths"])
    generator = ChatModel(raw["generator"]["provider_prefix"])
    reviewer = ChatModel(raw["reviewer"]["provider_prefix"])
    builder = MultiAgentDatasetBuilder(generator, reviewer, execute_read_only, schema, knowledge)
    failure = None
    try:
        cases, trace = builder.build(config, load_reference(args.reference))
    except BuildIncompleteError as error:
        cases, trace, failure = error.cases, error.trace, str(error)
    output = write_run_directory(Path(raw.get("output_root", "generated_datasets")), config, cases, trace, {
        "generator_model": generator.model, "reviewer_model": reviewer.model,
        "reference": args.reference, "build_failure": failure,
    })
    print(output)
    if failure:
        raise RuntimeError(f"{failure}; partial audit saved to {output}")


if __name__ == "__main__":
    main()


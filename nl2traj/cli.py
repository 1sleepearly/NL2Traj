"""Command-line entry point for public NL2Traj inference."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from .retrieval import TrajectorySelector
from .runner import NL2TrajRunner
from .runtime import UnifiedLLM


def database_config() -> dict:
    return {
        "host": os.getenv("DATABASE_HOST", "localhost"),
        "port": int(os.getenv("DATABASE_PORT", "5432")),
        "dbname": os.getenv("DATABASE_NAME", "trajectory_demo"),
        "user": os.getenv("DATABASE_USER", "postgres"),
        "password": os.getenv("DATABASE_PASSWORD", ""),
    }


def build_runner(args, records) -> NL2TrajRunner:
    llm = UnifiedLLM(
        provider=args.provider,
        api_key=os.getenv(f"{args.provider.upper()}_API_KEY"),
        api_url=os.getenv(f"{args.provider.upper()}_API_URL"),
        model=os.getenv(f"{args.provider.upper()}_MODEL"),
    )
    selector = TrajectorySelector(args.examples) if args.k > 0 else None
    if selector:
        selector.exclusion_mode = "strict"
        selector.set_test_gold_map({row["中文问题"]: row["SQL查询"] for row in records})
    return NL2TrajRunner(llm, database_config(), selector=selector, k=args.k)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run NL2Traj on a public-format workbook")
    parser.add_argument("input", help="Test workbook with 中文问题 and SQL查询 columns")
    parser.add_argument("--examples", default="data/examples/examples.xlsx")
    parser.add_argument("--output", default="results/nl2traj_predictions.jsonl")
    parser.add_argument("--provider", choices=["kimi", "deepseek", "gpt"], default="deepseek")
    parser.add_argument("--k", type=int, default=2)
    args = parser.parse_args()
    load_dotenv(override=False)

    frame = pd.read_excel(args.input)
    required = {"中文问题", "SQL查询"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Input workbook must contain: {sorted(required)}")
    records = frame.to_dict(orient="records")
    runner = build_runner(args, records)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in records:
            sql, answer, trace = runner.run(str(row["中文问题"]))
            handle.write(json.dumps({
                "difficulty": row.get("难度级别"),
                "question": row["中文问题"],
                "predicted_sql": sql,
                "predicted_answer": answer,
                "trace": trace,
            }, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()

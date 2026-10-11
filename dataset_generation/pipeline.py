"""Auditable multi-role construction of trajectory Text-to-SQL datasets."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, Protocol


TYPE_CATALOG = {
    "Easy": {
        "basic_filter_count": "single-step count or list with a direct attribute/date/time filter",
        "endpoint_time_value": "direct start/end time or point query",
        "whole_trajectory_metric": "one metric over a complete trajectory",
    },
    "Middle": {
        "od_relation": "combined origin/destination relation",
        "path_relation": "complete path intersects, passes, or avoids regions without clipping",
        "grouped_aggregation": "grouping and aggregation over trajectory records",
        "ranking_derived_metric": "ranking by a derived complete-trajectory metric",
    },
    "Hard": {
        "temporal_local_segment": "clip by time and measure a local segment",
        "spatial_local_segment": "clip by region and measure a local segment",
        "multi_region_path": "multi-region path constraints or segment-sensitive relations",
        "multistage_grouped_ranking": "intermediate results with grouped or nested ranking",
    },
}

DIFFICULTY_RUBRIC = {
    "Easy": "Single-step filtering, endpoint lookup, or one complete-trajectory metric.",
    "Middle": "Compositional query without local trajectory-segment construction.",
    "Hard": "Multi-stage spatio-temporal reasoning, clipping, or local-segment measurement.",
}


class TextModel(Protocol):
    def generate(self, prompt: str, system_prompt: str, temperature: float = 0.1) -> str: ...


@dataclass
class Candidate:
    id: str
    difficulty: str
    question: str
    semantic_spec: dict
    sql: str
    task_type: str
    operation_chain: list[str] = field(default_factory=list)
    difficulty_reason: str = ""
    output_spec: dict = field(default_factory=dict)
    evidence: str = ""
    answer: str | None = None
    review: dict = field(default_factory=dict)
    overlap_review: dict = field(default_factory=dict)
    result_review: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    human_status: str = "pending"

    def normalize(self) -> None:
        aliases = {"easy": "Easy", "middle": "Middle", "medium": "Middle", "hard": "Hard"}
        self.difficulty = aliases.get(self.difficulty.strip().lower(), self.difficulty.strip().title())
        self.question = " ".join(self.question.split())
        self.sql = " ".join(self.sql.split())


@dataclass
class BuildConfig:
    dataset_kind: str
    counts: dict[str, int]
    max_rounds: int = 3
    candidates_per_request: int = 2
    run_name: str = "trajectory"
    language: str = "Chinese"
    allow_empty_results: bool = False
    max_result_rows: int = 200


class BuildIncompleteError(RuntimeError):
    def __init__(self, message: str, cases: list[Candidate], trace: list[dict]):
        super().__init__(message)
        self.cases, self.trace = cases, trace


def _prompt(name: str) -> str:
    return (Path(__file__).parent / "prompts" / name).read_text(encoding="utf-8")


def _extract_json(text: str):
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.I | re.S).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.I | re.S)
    if fenced:
        text = fenced.group(1).strip()
    starts = [position for position in (text.find("["), text.find("{")) if position >= 0]
    if starts:
        text = text[min(starts):]
    return json.loads(text)


def mask_question(question: str) -> str:
    text = re.sub(r"\d{4}-\d{1,2}-\d{1,2}", "<DATE>", question)
    text = re.sub(r"\b\d+(?:\.\d+)?\b", "<NUMBER>", text)
    text = re.sub(r"[A-Za-z0-9_\u4e00-\u9fff]+(?:区|县|市)", "<REGION>", text)
    return " ".join(text.lower().split())


def sql_skeleton(sql: str) -> str:
    text = re.sub(r"'(?:''|[^'])*'", "<LITERAL>", sql.lower())
    text = re.sub(r"\b\d+(?:\.\d+)?\b", "<NUMBER>", text)
    return " ".join(text.split())


class OverlapIndex:
    def __init__(self, rows: Iterable[dict] = ()):
        self.questions, self.masked, self.sql = set(), set(), set()
        for row in rows:
            self.add(row["question"], row.get("gold_sql") or row.get("sql", ""))

    def add(self, question: str, sql: str) -> None:
        self.questions.add(" ".join(question.split()))
        self.masked.add(mask_question(question))
        if sql:
            self.sql.add(sql_skeleton(sql))

    def reasons(self, question: str, sql: str) -> list[str]:
        reasons = []
        if " ".join(question.split()) in self.questions:
            reasons.append("exact_question")
        if mask_question(question) in self.masked:
            reasons.append("masked_question")
        if sql and sql_skeleton(sql) in self.sql:
            reasons.append("sql_skeleton")
        return reasons


class MultiAgentDatasetBuilder:
    """Generator + independent reviews + deterministic and execution gates."""

    def __init__(self, generator: TextModel, reviewer: TextModel,
                 execute_sql: Callable[[str], str], schema: str, operator_knowledge: str):
        self.generator = generator
        self.reviewer = reviewer
        self.execute_sql = execute_sql
        self.schema = schema
        self.operator_knowledge = operator_knowledge

    def _generate(self, difficulty: str, task_type: str, count: int,
                  exclusions: list[str], feedback: list[str], language: str) -> list[Candidate]:
        request = {
            "task": "generate_candidates", "count": count, "difficulty": difficulty,
            "task_type": task_type, "task_type_definition": TYPE_CATALOG[difficulty][task_type],
            "language": language, "difficulty_rubric": DIFFICULTY_RUBRIC,
            "schema": self.schema, "operator_knowledge": self.operator_knowledge,
            "do_not_duplicate": exclusions[-100:], "previous_rejection_feedback": feedback[-10:],
        }
        raw = self.generator.generate(json.dumps(request, ensure_ascii=False), _prompt("generator.md"), 0.7)
        payload = _extract_json(raw)
        if isinstance(payload, dict):
            payload = payload.get("candidates") or payload.get("items") or [payload]
        if not isinstance(payload, list):
            raise ValueError("generator must return a candidate array")
        candidates = []
        for index, item in enumerate(payload):
            candidate = Candidate(
                id=str(item.get("id", f"C{index + 1:03d}")),
                difficulty=str(item.get("difficulty", difficulty)), question=str(item["question"]),
                semantic_spec=item.get("semantic_spec") or {}, sql=str(item["sql"]),
                task_type=str(item.get("task_type", task_type)),
                operation_chain=list(item.get("operation_chain") or []),
                difficulty_reason=str(item.get("difficulty_reason", "")),
                output_spec=item.get("output_spec") or {}, evidence=str(item.get("evidence", "")),
            )
            candidate.normalize()
            candidates.append(candidate)
        return candidates

    def _review(self, candidate: Candidate) -> dict:
        request = {"candidate": asdict(candidate), "schema": self.schema,
                   "operator_knowledge": self.operator_knowledge, "difficulty_rubric": DIFFICULTY_RUBRIC}
        result = _extract_json(self.reviewer.generate(
            json.dumps(request, ensure_ascii=False), _prompt("reviewer.md"), 0.0))
        if not isinstance(result, dict):
            raise ValueError("reviewer must return one object")
        return result

    def _overlap_review(self, candidate: Candidate, existing: list[dict]) -> dict:
        if not existing:
            return {"accept": True, "conflict_ids": [], "overlap_level": "none"}
        request = {"candidate": asdict(candidate), "existing_tasks": existing}
        return _extract_json(self.reviewer.generate(
            json.dumps(request, ensure_ascii=False), _prompt("overlap_reviewer.md"), 0.0))

    @staticmethod
    def _review_passes(review: dict) -> bool:
        return (review.get("accept") is True and review.get("sql_matches_question") is True
                and review.get("difficulty_matches") is True and review.get("task_type_matches") is True
                and review.get("language_ok") is True and not review.get("ambiguities")
                and not review.get("defects"))

    def build(self, config: BuildConfig, reference_rows: Iterable[dict] = ()) -> tuple[list[Candidate], list[dict]]:
        references = list(reference_rows)
        overlap = OverlapIndex(references)
        accepted: list[Candidate] = []
        trace: list[dict] = []
        exclusions = [row["question"] for row in references]
        feedback: list[str] = []
        targets = []
        for difficulty, count in config.counts.items():
            types = list(TYPE_CATALOG[difficulty])
            targets.extend((difficulty, types[index % len(types)]) for index in range(count))
        for difficulty, task_type in targets:
            completed = False
            for round_number in range(1, config.max_rounds + 1):
                try:
                    candidates = self._generate(difficulty, task_type, config.candidates_per_request,
                                                exclusions, feedback, config.language)
                except Exception as error:
                    trace.append({"round": round_number, "generation_error": str(error), "passed": False})
                    continue
                for candidate in candidates:
                    reasons = overlap.reasons(candidate.question, candidate.sql)
                    metadata_ok = bool(candidate.semantic_spec and candidate.operation_chain
                                       and candidate.difficulty_reason and candidate.output_spec)
                    language_ok = config.language != "Chinese" or bool(re.search(r"[\u4e00-\u9fff]", candidate.question))
                    review = self._review(candidate) if not reasons and metadata_ok and language_ok else {
                        "accept": False, "defects": ["failed_precheck"]}
                    candidate.review = review
                    semantic_ok = self._review_passes(review)
                    overlap_review = self._overlap_review(candidate, references + [asdict(x) for x in accepted]) \
                        if semantic_ok else {"accept": False, "reason": "skipped"}
                    candidate.overlap_review = overlap_review
                    answer, execution_error = None, None
                    if semantic_ok and overlap_review.get("accept") is True:
                        try:
                            answer = self.execute_sql(candidate.sql)
                        except Exception as error:
                            execution_error = str(error)
                    candidate.answer = answer
                    try:
                        rows = json.loads(answer) if answer is not None else None
                    except json.JSONDecodeError:
                        rows = None
                    result_ok = (isinstance(rows, list) and len(rows) <= config.max_result_rows
                                 and (config.allow_empty_results or bool(rows)))
                    candidate.validation = {
                        "overlap_reasons": reasons, "metadata_ok": metadata_ok,
                        "language_ok": language_ok, "semantic_review_ok": semantic_ok,
                        "overlap_review_ok": overlap_review.get("accept") is True,
                        "execution_ok": execution_error is None and answer is not None,
                        "execution_error": execution_error, "result_shape_ok": result_ok,
                    }
                    passed = all((not reasons, metadata_ok, language_ok, semantic_ok,
                                  overlap_review.get("accept") is True, execution_error is None, result_ok))
                    trace.append({"round": round_number, "candidate": asdict(candidate), "passed": passed})
                    if passed:
                        candidate.id = f"A{len(accepted) + 1:03d}"
                        accepted.append(candidate)
                        overlap.add(candidate.question, candidate.sql)
                        exclusions.append(candidate.question)
                        completed = True
                        break
                    feedback.append(json.dumps(candidate.validation, ensure_ascii=False))
                if completed:
                    break
            if not completed:
                raise BuildIncompleteError(f"could not build {difficulty}/{task_type}", accepted, trace)
        return accepted, trace


def write_run_directory(root: Path, config: BuildConfig, cases: list[Candidate],
                        trace: list[dict], metadata: dict) -> Path:
    run_id = f"{config.run_name}_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}"
    destination = root / run_id
    destination.mkdir(parents=True, exist_ok=False)
    prefix = "T" if config.dataset_kind == "test" else "E"
    records = []
    for index, candidate in enumerate(cases, 1):
        record = asdict(candidate)
        record.update({"source_candidate_id": record["id"], "id": f"{prefix}{index:03d}"})
        record["gold_sql"] = record.pop("sql")
        record["archived_answer"] = record.pop("answer")
        records.append(record)
    (destination / "cases.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    (destination / "trace.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in trace), encoding="utf-8")
    manifest = {"run_id": run_id, "status": "machine_validated_pending_human_confirmation",
                "human_confirmation_required": True, "case_count": len(cases), **metadata}
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination


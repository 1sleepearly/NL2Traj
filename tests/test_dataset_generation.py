import json

import pytest

from dataset_generation.pipeline import BuildConfig, BuildIncompleteError, MultiAgentDatasetBuilder, OverlapIndex


class FakeModel:
    def __init__(self, replies):
        self.replies = iter(replies)

    def generate(self, prompt, system_prompt, temperature=0.1):
        return next(self.replies)


def candidate():
    return [{
        "difficulty": "Easy", "task_type": "basic_filter_count", "question": "查询所有轨迹总数。",
        "semantic_spec": {"task": "count"}, "operation_chain": ["count"],
        "difficulty_reason": "single-step count", "output_spec": {"columns": ["count"]},
        "sql": "SELECT COUNT(*) FROM trips", "evidence": "direct count",
    }]


def accepted_review():
    return {
        "accept": True, "sql_matches_question": True, "difficulty_matches": True,
        "task_type_matches": True, "language_ok": True, "ambiguities": [], "defects": [],
    }


def test_constant_rewrites_are_detected():
    index = OverlapIndex([{"question": "查询 2020-01-01 的轨迹数量。", "sql": "SELECT 1 WHERE d='2020-01-01'"}])
    reasons = index.reasons("查询 2020-01-02 的轨迹数量。", "SELECT 1 WHERE d='2020-01-02'")
    assert "masked_question" in reasons
    assert "sql_skeleton" in reasons


def test_generator_review_and_execution_are_independent_gates():
    generator = FakeModel([json.dumps(candidate(), ensure_ascii=False)])
    reviewer = FakeModel([json.dumps(accepted_review()), json.dumps({"accept": True})])
    builder = MultiAgentDatasetBuilder(generator, reviewer, lambda sql: "[[1]]", "DDL", "knowledge")
    cases, trace = builder.build(BuildConfig("test", {"Easy": 1}, max_rounds=1, candidates_per_request=1))
    assert len(cases) == 1
    assert cases[0].human_status == "pending"
    assert trace[0]["passed"] is True


def test_execution_failure_blocks_acceptance():
    generator = FakeModel([json.dumps(candidate(), ensure_ascii=False)])
    reviewer = FakeModel([json.dumps(accepted_review()), json.dumps({"accept": True})])
    builder = MultiAgentDatasetBuilder(generator, reviewer, lambda sql: (_ for _ in ()).throw(RuntimeError("bad SQL")), "DDL", "knowledge")
    with pytest.raises(BuildIncompleteError):
        builder.build(BuildConfig("test", {"Easy": 1}, max_rounds=1, candidates_per_request=1))


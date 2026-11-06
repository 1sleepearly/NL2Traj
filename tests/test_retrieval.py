import json

from nl2traj.retrieval import SimilaritySelector


def test_generated_jsonl_can_be_selected_explicitly(tmp_path):
    path = tmp_path / "cases.jsonl"
    records = [
        {"question": "查询轨迹总数。", "masked_question": "查询轨迹总数。", "evidence": "count",
         "gold_sql": "SELECT COUNT(*) FROM trips"},
        {"question": "查询总路程。", "masked_question": "查询总路程。", "evidence": "length",
         "gold_sql": "SELECT SUM(length) FROM trips"},
    ]
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in records), encoding="utf-8")
    selector = SimilaritySelector(str(path))
    result = selector.select_top_k("请查询轨迹总数。", 1)
    assert result[0]["sql"] == "SELECT COUNT(*) FROM trips"

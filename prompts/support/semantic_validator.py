"""Deterministic question-to-SQL semantic checks used by NL2Traj selection.

These checks intentionally cover high-confidence trajectory distinctions.  They
are conservative: uncertain interpretations become warnings rather than hard
errors so a heuristic cannot discard an otherwise valid query.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from light_template import check_light_template, extract_light_template


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    penalty: int = 20

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ValidationReport:
    score: int
    issues: list[ValidationIssue]
    inferred_constraints: list[str]

    @property
    def blocking_issues(self) -> list[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def passed(self) -> bool:
        return not self.blocking_issues

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "passed": self.passed,
            "constraints": self.inferred_constraints,
            "issues": [issue.to_dict() for issue in self.issues],
        }

    def feedback_text(self) -> str:
        return "\n".join(f"[{x.code}] {x.message}" for x in self.issues)


def _has(sql: str, pattern: str) -> bool:
    return bool(re.search(pattern, sql, flags=re.I | re.S))


def _result_rows(answer):
    try:
        value = json.loads(str(answer))
        return value if isinstance(value, list) else None
    except (TypeError, ValueError, json.JSONDecodeError):
        return None


def validate_candidate(question: str, sql: str, answer=None) -> ValidationReport:
    q = str(question)
    s = str(sql)
    issues: list[ValidationIssue] = []
    constraints: list[str] = []

    def require(name: str, present: bool, code: str, message: str, penalty: int = 20):
        constraints.append(name)
        if not present:
            issues.append(ValidationIssue(code, message, "error", penalty))

    # Endpoint and path roles are the highest-confidence NL2Traj distinctions.
    if re.search(r"起点|出发地|从[^，。；]*出发", q):
        require("origin", _has(s, r"\bstartValue\s*\("), "origin_missing", "The question constrains the origin, but SQL does not use startValue().")
    if re.search(r"终点(?:在|位于|为)|目的地(?:在|位于|为)|到达[\u4e00-\u9fff]+区", q):
        require("destination", _has(s, r"\bendValue\s*\("), "destination_missing", "The question constrains the destination, but SQL does not use endValue().")
    if re.search(r"经过|途经|路径.*(?:穿过|通过)", q):
        path_test = _has(s, r"\btrajectory\s*\(|\batGeometry\s*\(")
        require("passing", path_test, "passing_missing", "A passing/path condition must inspect the trajectory process, not only an endpoint.", 25)
        require(
            "passing_predicate",
            _has(s, r"\bST_Intersects\s*\(|\batGeometry\s*\("),
            "passing_predicate_wrong",
            "经过/途经 requires path intersection or a spatial trajectory segment; ST_CoveredBy means the entire path stays inside.",
            30,
        )

    # A named peak normally selects a departure cohort.  Process clipping is
    # reserved for questions explicitly asking what happened during an interval.
    named_peak = bool(re.search(r"早高峰|晚高峰", q))
    explicit_process = bool(re.search(r"期间|时段内|区间内|正在|移动距离|移动时长|运行时长|区内", q))
    if named_peak and not explicit_process:
        arrival_scope = bool(re.search(r"到达|抵达|结束|终点时间", q))
        timestamp_fn = "endTimestamp" if arrival_scope else "startTimestamp"
        code = "peak_arrival_missing" if arrival_scope else "peak_departure_missing"
        require(f"peak_{'arrival' if arrival_scope else 'departure'}", _has(s, rf"\b{timestamp_fn}\s*\("), code, f"This peak-period cohort must be filtered by {timestamp_fn}().", 25)
        if _has(s, r"\batTime\s*\("):
            issues.append(ValidationIssue("peak_scope_wrong", "Do not atTime-clip an endpoint-time cohort; compute requested metrics on the complete trajectory.", "error", 30))

    # Administrative negation must still bind the endpoint to a real district.
    if re.search(r"终点不在[^，。；]*区|目的地不在[^，。；]*区", q):
        bound_elsewhere = _has(s, r"join\s+districts\b[\s\S]*\bendValue\s*\(") and _has(s, r"(?:name|adcode)\s*(?:<>|!=)")
        require("negative_destination_membership", bound_elsewhere, "negative_destination_unbound", "Bind endValue() to its actual district, then compare that district name/adcode with the excluded district.", 30)

    # Local metrics require a clipped temporal/spatial moving-point segment.
    metric_words = r"长度|距离|时长|持续时间|速度|路程"
    if re.search(rf"(?:区内|区域内|范围内|在[^，。；]*区内)[^，。；]*({metric_words})", q):
        require("local_spatial_segment", _has(s, r"\batGeometry\s*\("), "local_space_missing", "A region-qualified metric must be computed from an atGeometry() segment.", 25)
    if re.search(rf"(?:时段内|时间段内|期间)[^，。；]*(?:行驶|移动|轨迹片段)[^，。；]*({metric_words})", q):
        require("local_temporal_segment", _has(s, r"\batTime\s*\("), "local_time_missing", "A time-qualified metric must be computed from an atTime() segment.", 25)

    # Output grain and aggregation.
    aggregate = None
    if re.search(r"(?:总数|数量|多少条|几条)", q):
        aggregate = "count"
        require("count", _has(s, r"\bcount\s*\("), "aggregate_missing", "The requested count is not implemented with COUNT().")
    elif re.search(r"(?:总体|所有轨迹|全部轨迹).*(?:平均|均值)|平均(?:轨迹|行程)(?:长度|时长|距离)", q):
        aggregate = "avg"
        require("average", _has(s, r"\bavg\s*\("), "aggregate_missing", "The requested average is not implemented with AVG().")
    elif re.search(r"总(?:移动)?(?:长度|距离|路程|时长)", q):
        aggregate = "sum"
        require("sum", _has(s, r"\bsum\s*\("), "aggregate_missing", "The requested total metric is not implemented with SUM().")

    if re.search(r"按(?:日|日期|天|小时|行政区|区域)|每天|每日|每小时|各(?:日|天|区|区域|行政区)", q):
        require("grouping", _has(s, r"\bgroup\s+by\b|\bdistinct\s+on\b|\bpartition\s+by\b"), "grouping_missing", "The requested grouped output has no GROUP BY, PARTITION BY, or equivalent DISTINCT ON.")

    if re.search(r"最长|最短|最高|最低|最多|最少|排名|前\s*\d+", q):
        require("ranking", _has(s, r"\border\s+by\b"), "ranking_missing", "The ranking request has no ORDER BY.")
    limit_match = re.search(r"(?:前|最多(?:返回|显示)?)\s*(\d+)\s*(?:条|个|名)?", q)
    if limit_match:
        requested = int(limit_match.group(1))
        require(f"limit={requested}", _has(s, rf"\blimit\s+{requested}\b"), "limit_missing", f"The query must use LIMIT {requested}.")

    # Group-level average speed is an average of per-trip speeds, not a
    # distance-weighted ratio of aggregate distance to aggregate duration.
    grouped_speed = re.search(r"平均速度", q) and re.search(r"每天|每日|各日期|行政区", q)
    if grouped_speed:
        require("average_of_trip_speeds", _has(s, r"\bAVG\s*\("), "average_grain_wrong", "Use AVG(per-trip whole-trajectory speed), not SUM(distance)/SUM(duration).", 30)

    # 比例/占比 is stored as a fraction in this benchmark.  Percentage wording
    # is the only trigger for a factor of 100.
    if re.search(r"比例|占比", q) and not re.search(r"百分比|%", q):
        if _has(s, r"(?:\*\s*100\b|100(?:\.0+)?\s*\*)"):
            issues.append(ValidationIssue("ratio_scale_wrong", "比例/占比 must remain in the 0-to-1 scale; multiply by 100 only for 百分比 or %.", "error", 30))
        precision = re.search(r"保留\s*([一二三四五六七八九\d]+)\s*位", q)
        chinese_digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
        if precision:
            token = precision.group(1)
            digits = int(token) if token.isdigit() else chinese_digits.get(token)
            if digits is not None:
                require(f"ratio_round={digits}", _has(s, rf"\bROUND\s*\([\s\S]*,\s*{digits}\s*\)"), "ratio_rounding_missing", f"Round the requested ratio to {digits} decimal places.", 15)

    # High-confidence output contract for point-at-time queries seen in the
    # benchmark: retain the trajectory identifier and return readable WKT.
    if re.search(r"一条轨迹的位置", q):
        require("position_trip_id", _has(s, r"\btrip_id\b"), "output_trip_id_missing", "The requested trajectory position output must include trip_id.", 25)
        require("position_wkt", _has(s, r"\bST_AsText\s*\("), "output_geometry_unserialized", "Serialize the returned position with ST_AsText().", 20)

    # The light template adds cross-cutting checks that are awkward to express
    # as isolated keyword rules.  It remains deterministic and never becomes
    # an intermediate JSON-to-SQL generation stage.
    existing_messages = {issue.message for issue in issues}
    for message in check_light_template(extract_light_template(q), s):
        if message not in existing_messages:
            issues.append(ValidationIssue("light_template_mismatch", message, "error", 20))
            existing_messages.add(message)

    if re.search(r"不经过|未经过|没有经过|不在.*(?:区|区域)", q):
        require("negation", _has(s, r"\bnot\b|<>|!=|\bexcept\b"), "negation_missing", "The requested negation is missing from SQL.")

    rows = _result_rows(answer)
    if answer == "Success":
        issues.append(ValidationIssue("no_result_set", "The query produced no result set.", "error", 40))
    elif rows == []:
        issues.append(ValidationIssue("empty_result", "The query returned no rows; verify filters with a probe query.", "warning", 5))
    elif aggregate and rows is not None and len(rows) != 1 and not _has(s, r"\bgroup\s+by\b"):
        issues.append(ValidationIssue("unexpected_cardinality", "An ungrouped aggregate should normally return one row.", "warning", 8))

    score = max(0, 100 - sum(issue.penalty for issue in issues))
    return ValidationReport(score, issues, constraints)


def validate_template_candidate(template: dict, sql: str, answer=None) -> ValidationReport:
    """Check whether SQL realizes a normalized Trajectory Semantic Template."""
    s = str(sql)
    issues: list[ValidationIssue] = []
    constraints: list[str] = []

    def require(name: str, present: bool, code: str, message: str, penalty: int = 20):
        constraints.append(name)
        if not present:
            issues.append(ValidationIssue(code, message, "error", penalty))

    temporal = template.get("temporal_constraints", [])
    spatial = template.get("spatial_constraints", [])
    for item in spatial:
        target = item.get("target")
        if target == "origin":
            require("template.origin", _has(s, r"\bstartValue\s*\("), "origin_missing", "Template origin is not realized with startValue().")
        elif target == "destination":
            require("template.destination", _has(s, r"\bendValue\s*\("), "destination_missing", "Template destination is not realized with endValue().")
        elif target == "passing":
            require("template.passing", _has(s, r"\btrajectory\s*\(|\batGeometry\s*\("), "passing_missing", "Template passing role is not realized on the trajectory process.", 25)

    for computation in template.get("trajectory_computations", []):
        if computation.get("scope") != "local_segment":
            continue
        refs = computation.get("segment_constraints", [])
        needs_time = any(str(ref).startswith("temporal_constraints[") for ref in refs)
        needs_space = any(str(ref).startswith("spatial_constraints[") for ref in refs)
        if needs_time:
            require("template.temporal_clip", _has(s, r"\batTime\s*\("), "local_time_missing", "Template local temporal segment is not realized with atTime().", 25)
        if needs_space:
            require("template.spatial_clip", _has(s, r"\batGeometry\s*\("), "local_space_missing", "Template local spatial segment is not realized with atGeometry().", 25)

    aggregations = {str(x.get("aggregation", "none")).lower() for x in template.get("outputs", [])}
    for name in aggregations & {"count", "sum", "avg", "min", "max"}:
        require(f"template.aggregate.{name}", _has(s, rf"\b{name}\s*\("), "aggregate_missing", f"Template aggregation {name.upper()} is absent from SQL.")

    if template.get("group_by"):
        require("template.grouping", _has(s, r"\bgroup\s+by\b|\bpartition\s+by\b|\bdistinct\s+on\b"), "grouping_missing", "Template grouping is absent from SQL.")
    if template.get("order_by"):
        require("template.ranking", _has(s, r"\border\s+by\b"), "ranking_missing", "Template ordering is absent from SQL.")
    if template.get("limit") is not None:
        limit = int(template["limit"])
        require(f"template.limit={limit}", _has(s, rf"\blimit\s+{limit}\b"), "limit_missing", f"Template LIMIT {limit} is absent from SQL.")

    rows = _result_rows(answer)
    if answer == "Success":
        issues.append(ValidationIssue("no_result_set", "The query produced no result set.", "error", 40))
    elif rows == []:
        issues.append(ValidationIssue("empty_result", "The query returned no rows.", "warning", 5))

    score = max(0, 100 - sum(issue.penalty for issue in issues))
    return ValidationReport(score, issues, constraints)

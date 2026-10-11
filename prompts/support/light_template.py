"""Deterministic light semantic templates for direct NL2Traj generation.

The template is never an intermediate generation target.  It is extracted
without an LLM and is used only for prompt emphasis, example ranking, and
post-generation consistency checks.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class LightTemplate:
    time_role: str | None
    origin: bool
    destination: bool
    passing: bool
    output_id: bool
    output_position: bool
    output_speed: bool
    output_distance: bool
    output_date: bool
    grouped_average_speed: bool
    ratio_fraction: bool
    ordered_passing: int
    forbidden_invented_date: bool
    deterministic_single: bool
    endpoint_ratio_population: bool
    requested_precision: int | None


def extract_light_template(question: str) -> LightTemplate:
    q = str(question)
    named_period = bool(re.search(r"早高峰|晚高峰", q))
    process = bool(re.search(r"期间|时段内|区间内|正在|移动距离|移动时长|运行时长", q))
    explicit_departure = bool(re.search(r"出发时间|出发时刻|高峰[^，。；]*出发|早高峰从|晚高峰从", q))
    if explicit_departure and named_period and not process:
        time_role = "departure"
    elif re.search(r"到达|抵达|结束", q) and named_period and not process:
        time_role = "arrival"
    elif named_period and not process:
        time_role = "departure"
    elif process or re.search(r"\d{1,2}:\d{2}.*(?:位置|行驶|移动)", q):
        time_role = "process"
    else:
        time_role = None

    regions = re.findall(r"[\u4e00-\u9fff]{1,8}(?:区|县|市)", q)
    ordered = len(regions) if re.search(r"依次|按顺序|先.+再|先.+最终", q) else 0
    precision_match = re.search(r"保留\s*([一二三四五六七八九\d]+)\s*位", q)
    digit_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    precision = None
    if precision_match:
        token = precision_match.group(1)
        precision = int(token) if token.isdigit() else digit_map.get(token)

    return LightTemplate(
        time_role=time_role,
        origin=bool(re.search(r"起点|出发地|从[^，。；]*出发", q)),
        destination=bool(re.search(r"终点(?:在|位于)|目的地(?:在|位于)|到达[^，。；]*区", q)),
        passing=bool(re.search(r"经过|途经", q)),
        output_id=bool(re.search(r"(?:轨迹|行程)\s*(?:ID|编号)|一条轨迹", q, re.I)),
        output_position="位置" in q,
        output_speed=bool(re.search(r"速度|时速", q)),
        output_distance=bool(re.search(r"距离|长度|路程", q)),
        output_date=bool(re.search(r"每天|每日|各日期|日期", q)),
        grouped_average_speed=bool(re.search(r"平均速度", q) and re.search(r"每天|每日|各日期|行政区", q)),
        ratio_fraction=bool(re.search(r"比例|占比", q) and not re.search(r"百分比|%", q)),
        ordered_passing=ordered,
        forbidden_invented_date=not bool(re.search(r"\d{4}-\d{2}-\d{2}", q)),
        deterministic_single=bool(re.search(r"一条|一个|最小|最大|最高|最低|最近", q)),
        endpoint_ratio_population=bool(re.search(r"比例|占比", q) and re.search(r"起点和终点都在|起终点都在", q)),
        requested_precision=precision,
    )


def format_template_emphasis(template: LightTemplate) -> str:
    lines = []
    for key, value in asdict(template).items():
        if value not in (False, None, 0, ""):
            lines.append(f"- {key}: {value}")
    if not lines:
        return ""
    return "/* Deterministically extracted semantic emphasis:\n" + "\n".join(lines) + "\n*/\n"


def template_similarity(target: LightTemplate, example: LightTemplate) -> float:
    left, right = asdict(target), asdict(example)
    keys = [key for key, value in left.items() if value not in (False, None, 0, "")]
    if not keys:
        return 0.0
    important = {"time_role", "grouped_average_speed", "ratio_fraction", "ordered_passing"}
    total = sum(2.0 if key in important else 1.0 for key in keys)
    matched = sum((2.0 if key in important else 1.0) for key in keys if left[key] == right[key])
    return matched / total


def check_light_template(template: LightTemplate, sql: str) -> list[str]:
    s = str(sql)
    issues: list[str] = []

    def has(pattern: str) -> bool:
        return bool(re.search(pattern, s, flags=re.I | re.S))

    if template.time_role == "departure" and not has(r"startTimestamp\s*\("):
        issues.append("time role is departure but startTimestamp() is absent")
    if template.time_role == "arrival" and not has(r"endTimestamp\s*\("):
        issues.append("time role is arrival but endTimestamp() is absent")
    if template.time_role == "process" and not has(r"atTime\s*\(|valueAtTimestamp\s*\(|&&\s*tstzspan"):
        issues.append("process-time operation is absent")
    if template.origin and not has(r"startValue\s*\("):
        issues.append("origin role is absent")
    if template.destination and not has(r"endValue\s*\("):
        issues.append("destination role is absent")
    if template.passing and not has(r"ST_Intersects\s*\(|atGeometry\s*\("):
        issues.append("passing role is not implemented as path intersection")
    if template.output_id and not has(r"\btrip_id\b"):
        issues.append("requested trip_id is absent")
    if template.output_position and not has(r"valueAtTimestamp\s*\("):
        issues.append("requested position is absent")
    if template.output_position and not has(r"ST_AsText\s*\("):
        issues.append("position is not serialized as text")
    if template.output_speed and not has(r"\*\s*3\.6|3\.6\s*\*"):
        issues.append("requested km/h speed expression is absent")
    if template.output_distance and not has(r"ST_(?:Length|Distance|DWithin)\s*\("):
        issues.append("requested distance/length expression is absent")
    if template.output_date and not has(r"\btrip_date\b"):
        issues.append("requested date output/grouping is absent")
    if template.grouped_average_speed and not has(r"\bAVG\s*\("):
        issues.append("grouped average speed is not AVG(per-trip speed)")
    if template.ratio_fraction and has(r"\*\s*100\b|100(?:\.0+)?\s*\*"):
        issues.append("ratio was incorrectly converted to percentage")
    if template.forbidden_invented_date and has(r"(?:DATE|TIMESTAMPTZ)\s*'\d{4}-\d{2}-\d{2}"):
        issues.append("SQL invented a date absent from the question")
    if template.deterministic_single and has(r"\bLIMIT\s+1\b") and not has(r"\bORDER\s+BY\b"):
        issues.append("single-row output is nondeterministic because LIMIT 1 has no ORDER BY tie-break")
    if template.endpoint_ratio_population:
        raw_denominator = has(r"NULLIF\s*\(\s*COUNT\s*\(\s*\*\s*\)\s*,")
        endpoint_filtered_population = (
            has(r"FROM\s+\w+\s+WHERE[^;]*(?:start_in|startValue)[^;]*(?:end_in|endValue)")
            or has(r"JOIN\s+districts\b[\s\S]*startValue\s*\([\s\S]*endValue\s*\(")
        )
        if raw_denominator and not endpoint_filtered_population:
            issues.append("ratio denominator is all trips instead of the stated origin-and-destination population")
    if template.requested_precision is not None and not has(rf"ROUND\s*\([\s\S]*,\s*{template.requested_precision}\s*\)"):
        issues.append(f"requested rounding to {template.requested_precision} decimal places is absent")
    if template.ordered_passing:
        comparisons = len(re.findall(r"startTimestamp\s*\([^)]*\)\s*<\s*startTimestamp", s, flags=re.I))
        if comparisons < template.ordered_passing - 1:
            issues.append(f"ordered passing needs {template.ordered_passing - 1} segment-time comparisons")
    return issues

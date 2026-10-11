"""Structured diagnostics for SQL execution and semantic validation failures."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ErrorDiagnosis:
    category: str
    summary: str
    repair_scope: str
    retryable: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    def to_feedback(self, detail: str = "") -> str:
        detail_line = f"\nObserved detail: {detail.strip()}" if detail else ""
        return (
            "Structured correction request:\n"
            f"- error_type: {self.category}\n"
            f"- diagnosis: {self.summary}\n"
            f"- repair_scope: {self.repair_scope}\n"
            "- instruction: Preserve correct clauses and change only what is needed. "
            "Return exactly one corrected read-only SELECT/WITH query."
            f"{detail_line}"
        )


_EXECUTION_RULES = (
    (r"does not exist|undefined (?:table|column|function)|no function matches", "schema_mismatch",
     "A referenced table, column, or function is unavailable or has the wrong signature.", "schema/operator reference"),
    (r"syntax error|unterminated|mismatched|at or near", "sql_syntax",
     "The generated SQL is not syntactically valid.", "syntax, aliases, or CTE structure"),
    (r"cannot cast|invalid input syntax|operator does not exist|datatype mismatch|type .* does not exist", "type_mismatch",
     "An expression uses incompatible PostgreSQL/PostGIS/MobilityDB types.", "the failing expression and its casts"),
    (r"statement timeout|canceling statement|timeout", "query_timeout",
     "The query exceeded the execution budget.", "filter placement and query plan"),
    (r"division by zero", "arithmetic_error",
     "The query does not guard a zero denominator.", "the affected arithmetic expression"),
    (r"permission denied|read-only transaction", "unsafe_or_forbidden_sql",
     "The query attempted an operation outside the read-only contract.", "replace the statement with a SELECT query", False),
)


def diagnose_execution_error(error: str) -> ErrorDiagnosis:
    text = str(error).lower()
    for pattern, category, summary, scope, *retryable in _EXECUTION_RULES:
        if re.search(pattern, text):
            return ErrorDiagnosis(category, summary, scope, retryable[0] if retryable else True)
    return ErrorDiagnosis(
        "execution_error",
        "The database rejected the generated query.",
        "the clause identified by the database error",
    )


def extract_sspa_schema_tip(error: str) -> str | None:
    """Paper-bounded SSpa tips: missing relation/column/function or ambiguity only."""
    detail = str(error).removeprefix("ERROR:").strip()
    patterns = (
        (r'relation "([^"]+)" does not exist', 'The table "{}" does not exist and should not be used.'),
        (r'column "([^"]+)" does not exist', 'The column "{}" does not exist and should not be used.'),
        (r'function ([^(\s]+)', 'The function "{}" is unavailable with the generated signature.'),
        (r'column reference "([^"]+)" is ambiguous', 'The column "{}" is ambiguous; qualify it with a table alias.'),
    )
    for pattern, template in patterns:
        match = re.search(pattern, detail, flags=re.IGNORECASE)
        if match:
            return template.format(match.group(1))
    return None


def diagnose_semantic_issues(issues) -> ErrorDiagnosis:
    codes = {getattr(issue, "code", "") for issue in issues}
    if codes & {"origin_missing", "destination_missing", "passing_missing", "negation_missing"}:
        return ErrorDiagnosis(
            "wrong_spatial_semantics",
            "The SQL does not preserve one or more requested trajectory spatial roles.",
            "spatial predicates only",
        )
    if codes & {"local_space_missing", "local_time_missing"}:
        return ErrorDiagnosis(
            "wrong_trajectory_scope",
            "A metric requested for a local trajectory segment is computed on the whole trajectory.",
            "segment construction and the dependent metric",
        )
    if codes & {"aggregate_missing", "grouping_missing"}:
        return ErrorDiagnosis(
            "wrong_aggregation",
            "The SQL aggregation or grouping does not match the requested output grain.",
            "SELECT, GROUP BY, and aggregate expressions",
        )
    if codes & {"ranking_missing", "limit_missing"}:
        return ErrorDiagnosis(
            "wrong_ranking",
            "The requested ranking or result limit is not implemented.",
            "ORDER BY and LIMIT",
        )
    return ErrorDiagnosis(
        "semantic_mismatch",
        "The SQL is executable but violates constraints inferred from the question.",
        "only the clauses named by the validation issues",
    )

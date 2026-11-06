"""Complete NL2Traj inference pipeline used in the experiments."""

from __future__ import annotations

import ast
import collections
import json
import re
import time

from .error_diagnostics import diagnose_execution_error, diagnose_semantic_issues
from .prompt_builder import build_prompt
from .runtime import clean_sql, execute_sql
from .semantic_validator import validate_candidate


class NL2TrajRunner:
    """Retrieve demonstrations, generate candidates, validate, repair, select."""

    vote_n = 5
    initial_vote_n = 2
    semantic_repair_n = 2

    def __init__(self, llm, db_params: dict, selector=None, k: int = 2):
        self.llm = llm
        self.db_params = dict(db_params)
        self.selector = selector
        self.k = k
        self.last_trace: dict = {}

    @staticmethod
    def _parse_answer_rows(value):
        if value is None or isinstance(value, list):
            return value
        text = str(value).strip()
        if not text or text.startswith("ERROR:"):
            return None
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(text)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return None

    @staticmethod
    def _clean_candidate_sql(raw_sql):
        sql = clean_sql(raw_sql)
        sql = re.sub(r"\s+", " ", sql.replace("\n", " ").replace("\r", " ")).strip()
        first = re.search(r"\b(WITH|SELECT)\b", sql, flags=re.IGNORECASE)
        if first:
            sql = sql[first.start():].strip()
        elif sql:
            sql = "SELECT " + sql
        parts = [part.strip() for part in sql.split(";") if part.strip()]
        if parts:
            sql = parts[0]
        return sql + ("" if sql.endswith(";") else ";")

    @staticmethod
    def _normalize_value(value):
        if value is None:
            return None
        try:
            return round(float(str(value).strip()), 8)
        except Exception:
            return str(value).strip()

    def _denotation_key(self, answer):
        rows = self._parse_answer_rows(answer)
        if rows is None:
            return str(answer).strip()
        normalized = []
        for row in rows:
            values = row if isinstance(row, (list, tuple)) else [row]
            normalized.append([self._normalize_value(value) for value in values])
        normalized.sort(key=repr)
        return repr(normalized)

    def _evaluate(self, question, sql, candidate_index):
        answer = execute_sql(sql, self.db_params)
        result = {"candidate_index": candidate_index, "sql": sql, "ans": answer}
        if str(answer).startswith("ERROR:") or str(answer).strip() == "TIMEOUT":
            detail = str(answer).removeprefix("ERROR:").strip()
            result.update(execution_diagnosis=diagnose_execution_error(detail), validation=None)
        else:
            result.update(execution_diagnosis=None, validation=validate_candidate(question, sql, answer))
        return result

    def _select(self, candidates):
        groups = collections.OrderedDict()
        for candidate in candidates:
            groups.setdefault(self._denotation_key(candidate["ans"]), []).append(candidate)
        for key, group in groups.items():
            bonus = min(15, 5 * (len(group) - 1))
            for candidate in group:
                candidate["agreement_count"] = len(group)
                candidate["selection_score"] = candidate["validation"].score + bonus
        selected = max(candidates, key=lambda item: (
            item["validation"].passed,
            item["selection_score"],
            item["agreement_count"],
            -item["candidate_index"],
        ))
        reason = (
            f"candidate={selected['candidate_index']}; semantic={selected['validation'].score}/100; "
            f"agreement={selected['agreement_count']}/{len(candidates)}; passed={selected['validation'].passed}"
        )
        return selected, reason

    def _repair(self, question, candidate, examples, repair_index):
        if candidate.get("execution_diagnosis"):
            diagnosis = candidate["execution_diagnosis"]
            feedback = diagnosis.to_feedback(str(candidate["ans"]).removeprefix("ERROR:").strip())
        else:
            report = candidate["validation"]
            diagnosis = diagnose_semantic_issues(report.issues)
            feedback = diagnosis.to_feedback(report.feedback_text())
        prompt = build_prompt(question, feedback=f"{feedback}\nPrevious SQL:\n{candidate['sql']}", examples=examples)
        raw = self.llm.generate(prompt, system_prompt="You repair MobilityDB SQL using typed execution and semantic feedback.", temperature=0.1)
        repaired = self._evaluate(question, self._clean_candidate_sql(raw), self.vote_n + repair_index)
        repaired.update(repair_of=candidate["candidate_index"], repair_type=diagnosis.category)
        return repaired

    @staticmethod
    def _trace(candidate):
        diagnosis, validation = candidate.get("execution_diagnosis"), candidate.get("validation")
        return {
            "candidate_index": candidate["candidate_index"],
            "repair_of": candidate.get("repair_of"),
            "repair_type": candidate.get("repair_type"),
            "sql": candidate["sql"],
            "answer": candidate["ans"],
            "execution_diagnosis": diagnosis.to_dict() if diagnosis else None,
            "validation": validation.to_dict() if validation else None,
            "agreement_count": candidate.get("agreement_count"),
            "selection_score": candidate.get("selection_score"),
        }

    def run(self, question: str) -> tuple[str, str, dict]:
        examples = self.selector.format_examples_for_prompt(question, self.k) if self.selector and self.k > 0 else ""
        prompt = build_prompt(question, examples=examples)
        system = "You are an expert in spatial-temporal databases (MobilityDB)."
        results = []
        for index in range(self.initial_vote_n):
            if index:
                time.sleep(2)
            raw = self.llm.generate(prompt, system_prompt=system, temperature=1.0)
            results.append(self._evaluate(question, self._clean_candidate_sql(raw), index + 1))
        first_two_agree = all(x["validation"] and x["validation"].passed for x in results) and self._denotation_key(results[0]["ans"]) == self._denotation_key(results[1]["ans"])
        if not first_two_agree:
            for index in range(self.initial_vote_n, self.vote_n):
                time.sleep(2)
                raw = self.llm.generate(prompt, system_prompt=system, temperature=1.0)
                results.append(self._evaluate(question, self._clean_candidate_sql(raw), index + 1))
        valid = [item for item in results if item["validation"] is not None]
        selected, reason = self._select(valid) if valid else (results[0], "All initial candidates failed execution.")
        repairs = []
        all_empty = bool(valid) and all(item["ans"] == "[]" for item in valid)
        for repair_index in range(1, self.semantic_repair_n + 1):
            if selected.get("validation") and selected["validation"].passed and not all_empty:
                break
            repaired = self._repair(question, selected, examples, repair_index)
            repairs.append(repaired)
            results.append(repaired)
            if repaired["validation"] is not None:
                valid.append(repaired)
                selected, reason = self._select(valid)
                all_empty = all(item["ans"] == "[]" for item in valid)
            else:
                selected = repaired
        if valid:
            selected, reason = self._select(valid)
        self.last_trace = {
            "candidates": [self._trace(item) for item in results],
            "selection_reason": reason,
            "repair_count": len(repairs),
            "initial_candidates_agree": first_two_agree,
            "initial_generated": self.initial_vote_n if first_two_agree else self.vote_n,
        }
        return selected["sql"], selected["ans"], self.last_trace

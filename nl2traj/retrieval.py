"""
similarity_selector.py
======================
掩码问题相似度选择法（Masked Question Similarity，MQS）

样例集的"掩码问题"列已在正式样例池中预计算并写入 xlsx，
本模块直接读取该列进行检索；可选的泄漏审计模式会对样例原文再次掩码以排除同模板样例。

目标问题在查询时仍需掩码（复用与 fresh.py 相同的规则），
通过 mask_question() 完成，之后与样例矩阵做余弦相似度比较。

依赖：scikit-learn, pandas；读取 xlsx 时还需 openpyxl
"""

import re
import sys
import os
import json
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .light_template import extract_light_template, template_similarity

# ---------------------------------------------------------------------------
# 目标问题掩码函数（与正式样例池生成规则保持一致）
# 仅掩"具体值"类 token（时间、坐标、数字、引号内文），保留所有结构词
# ---------------------------------------------------------------------------
_MASK_RULES = [
    (re.compile(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'), '[TIME]'),
    (re.compile(r'\d{4}-\d{2}-\d{2}'),                     '[DATE]'),
    (re.compile(r'\d{1,2}:\d{2}(:\d{2})?'),                '[TIME]'),
    (re.compile(r'\(\s*\d+\.\d+\s*,\s*\d+\.\d+\s*\)'),     '[COORD]'),
    (re.compile(r'[\u201c\u201d][^\u201c\u201d]*[\u201c\u201d]'), '[VAL]'),
    (re.compile(r'「[^」]*」'),                               '[VAL]'),
    (re.compile(r'\d+(\.\d+)?'),                             '[NUM]'),
]

def mask_question(question: str) -> str:
    """对目标问题做通用掩码，与样例集 fresh.py 中预处理规则一致。"""
    q = question
    for pattern, placeholder in _MASK_RULES:
        q = pattern.sub(placeholder, q)
    return q


def lexical_sql_skeleton(sql: str) -> str:
    """Replace SQL literals for conservative evaluation-only overlap filtering."""
    sql = str(sql).lower()
    sql = re.sub(r"'[^']*'", "'[LITERAL]'", sql)
    sql = re.sub(r"\b\d+(?:\.\d+)?\b", "[NUM]", sql)
    return re.sub(r"\s+", " ", sql).strip()


# ---------------------------------------------------------------------------
# 相似度选择器
# ---------------------------------------------------------------------------

class SimilaritySelector:
    """
    从样例集中为目标问题选取 Top-K 最相似样例。

    样例集的掩码已在正式构建流程中预计算并存入 xlsx 的
    「掩码问题」列，本类初始化时直接读取，不做任何运行时掩码操作。

    Parameters
    ----------
    examples_path : str
        样例集 xlsx 或生成器产出的 cases.jsonl 路径。
    question_col : str
        原始问题列名，默认 '中文题目'。
    masked_col : str
        预计算掩码列名，默认 '掩码问题'。
    sql_col : str
        SQL 列名，默认 'SQL查询'。
    """

    def __init__(
        self,
        examples_path: str = 'data/examples/examples_v2.xlsx',
        question_col: str = '中文题目',
        masked_col: str = '掩码问题',
        evidence_col: str = '证据',
        sql_col: str = 'SQL查询',
    ):
        path = Path(examples_path)
        if path.suffix.lower() == '.jsonl':
            rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
            df = pd.DataFrame({
                question_col: [row.get('question', '') for row in rows],
                masked_col: [row.get('masked_question') or mask_question(row.get('question', '')) for row in rows],
                evidence_col: [row.get('evidence', '') for row in rows],
                sql_col: [row.get('gold_sql') or row.get('sql', '') for row in rows],
            })
        elif path.suffix.lower() == '.xlsx':
            df = pd.read_excel(path)
        else:
            raise ValueError("样例集仅支持 .xlsx 或 .jsonl")

        if masked_col not in df.columns:
            raise ValueError(
                f"样例集缺少「{masked_col}」列，请重新生成正式样例池。"
            )

        self.questions: list[str] = df[question_col].fillna('').astype(str).tolist()
        self.evidences: list[str] = df[evidence_col].fillna('').astype(str).tolist() if evidence_col in df.columns else [''] * len(df)
        self.sqls: list[str] = df[sql_col].fillna('').astype(str).tolist()
        if not self.questions or any(not question for question in self.questions):
            raise ValueError("样例集不能为空，且每条样例必须有问题")
        if any(not sql for sql in self.sqls):
            raise ValueError("每条样例必须有 SQL")
        self.example_skeletons = [lexical_sql_skeleton(sql) for sql in self.sqls]
        self.test_gold_map: dict[str, str] = {}
        self.exclusion_mode = os.getenv("TRAJ_EXAMPLE_EXCLUSION", "none").strip().lower()
        if self.exclusion_mode not in {"none", "exact", "masked", "skeleton", "strict"}:
            raise ValueError("TRAJ_EXAMPLE_EXCLUSION must be none, exact, masked, skeleton, or strict")
        self.audit_path = os.getenv("TRAJ_EXAMPLE_AUDIT_PATH", "").strip()
        # 直接使用预计算好的掩码，不在运行时处理样例集
        masked_examples: list[str] = df[masked_col].fillna('').astype(str).tolist()
        self.masked_examples = masked_examples

        self._vectorizer = TfidfVectorizer(
            analyzer='char_wb',
            ngram_range=(2, 4),
            min_df=1,
        )
        self._example_matrix = self._vectorizer.fit_transform(masked_examples)

        print(
            f"[SimilaritySelector] 已加载 {len(self.questions)} 条样例（掩码列: '{masked_col}'），"
            f"TF-IDF 维度: {self._example_matrix.shape[1]}"
        )

    # ------------------------------------------------------------------
    def select_top_k(self, target_question: str, k: int) -> list[dict]:
        """选取与目标问题最相似的 Top-K 样例。"""
        k = min(k, len(self.questions))
        masked_target = mask_question(target_question)
        target_vec = self._vectorizer.transform([masked_target])
        sims = cosine_similarity(target_vec, self._example_matrix)[0]

        ordered = sims.argsort()[::-1]
        target_skeleton = self.test_gold_map.get(target_question)
        if self.exclusion_mode in {"skeleton", "strict"} and target_skeleton is None:
            raise ValueError("Evaluation-only SQL skeleton exclusion requires a test gold map")
        eligible = []
        for idx in ordered:
            if self.exclusion_mode in {"exact", "strict"} and self.questions[idx] == target_question:
                continue
            if self.exclusion_mode in {"masked", "strict"} and masked_examples_equal(masked_target, self.questions[idx]):
                continue
            if self.exclusion_mode in {"skeleton", "strict"} and self.example_skeletons[idx] == target_skeleton:
                continue
            eligible.append(idx)
            if len(eligible) == k:
                break
        if len(eligible) != k:
            raise ValueError(f"Only {len(eligible)} eligible examples remain for k={k}")
        selected = [
            {
                'rank':       rank,
                'similarity': float(sims[idx]),
                'question':   self.questions[idx],
                'evidence':   self.evidences[idx],
                'sql':        self.sqls[idx],
            }
            for rank, idx in enumerate(eligible, start=1)
        ]
        if self.audit_path:
            audit = Path(self.audit_path)
            audit.parent.mkdir(parents=True, exist_ok=True)
            with audit.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"target_question": target_question, "mode": self.exclusion_mode,
                                         "selected": [{"rank": item["rank"], "similarity": item["similarity"],
                                                       "question": item["question"]} for item in selected]}, ensure_ascii=False) + "\n")
        return selected

    def set_test_gold_map(self, records: dict[str, str]) -> None:
        """Benchmark-only exclusions; gold SQL is never inserted into a model prompt."""
        if len(records) != len(set(records)):
            raise ValueError("Duplicate test questions are not supported")
        self.test_gold_map = {question: lexical_sql_skeleton(sql) for question, sql in records.items()}

    def format_examples_for_prompt(self, target_question: str, k: int) -> str:
        """Format the selected examples for the existing few-shot prompt."""
        if k <= 0:
            return ''
        selected = self.select_top_k(target_question, k)
        lines = [f'/* Few-shot Examples (K={k}, Masked Question Similarity):']
        for item in selected:
            lines.append(f"Q{item['rank']}: {item['question']}")
            if item.get('evidence'):
                lines.append(f"Hint{item['rank']}: {item['evidence']}")
            lines.append(f"A{item['rank']}: {item['sql']}")
            lines.append('')
        lines.append('*/')
        return '\n'.join(lines)


def _skeleton_tokens(sql: str) -> set[str]:
    return set(re.findall(r"[a-z_]+|[(),.*=<>]", lexical_sql_skeleton(sql)))


def trajectory_semantic_tags(text: str) -> set[str]:
    """High-level trajectory operations used to rerank NL2Traj examples."""
    rules = {
        "origin": r"起点|出发|从.+到",
        "destination": r"终点|到达|从.+到",
        "passing": r"经过|途经|路径",
        "time_clip": r"期间|时段内|时间段内",
        "space_clip": r"区内|区域内|内部",
        "distance": r"距离|长度|路程",
        "duration": r"时长|持续时间|用时",
        "speed": r"速度|时速",
        "ranking": r"最长|最短|最高|最低|最多|最少|前\s*\d+|排名",
        "ratio": r"比例|占比|百分比",
        "group": r"每日|每天|各日|各区|按.+统计",
    }
    return {name for name, pattern in rules.items() if re.search(pattern, str(text))}


class TrajectorySelector(SimilaritySelector):
    """NL2Traj retrieval: trajectory-operation overlap, then lexical fit.

    Exclusions are inherited from SimilaritySelector.  In formal benchmark
    runs the runner enables strict mode, which removes exact, masked-equal,
    and gold-SQL-skeleton-equal examples before anything reaches the prompt.
    """

    def select_top_k(self, target_question: str, k: int) -> list[dict]:
        k = min(k, len(self.questions))
        masked_target = mask_question(target_question)
        target_vec = self._vectorizer.transform([masked_target])
        lexical = cosine_similarity(target_vec, self._example_matrix)[0]
        target_tags = trajectory_semantic_tags(target_question)
        target_template = extract_light_template(target_question)
        target_skeleton = self.test_gold_map.get(target_question)
        if self.exclusion_mode in {"skeleton", "strict"} and target_skeleton is None:
            raise ValueError("Evaluation-only SQL skeleton exclusion requires a test gold map")

        ranked = []
        for idx, example in enumerate(self.questions):
            if self.exclusion_mode in {"exact", "strict"} and example == target_question:
                continue
            if self.exclusion_mode in {"masked", "strict"} and masked_examples_equal(masked_target, example):
                continue
            if self.exclusion_mode in {"skeleton", "strict"} and self.example_skeletons[idx] == target_skeleton:
                continue
            example_tags = trajectory_semantic_tags(example)
            union = target_tags | example_tags
            semantic = len(target_tags & example_tags) / len(union) if union else 0.0
            template_score = template_similarity(target_template, extract_light_template(example))
            ranked.append((template_score, semantic, float(lexical[idx]), -idx, idx))

        ranked.sort(reverse=True)
        if len(ranked) < k:
            raise ValueError(f"Only {len(ranked)} eligible examples remain for k={k}")
        return [
            {
                "rank": rank,
                "similarity": lexical_score,
                "semantic_similarity": semantic_score,
                "question": self.questions[idx],
                "evidence": self.evidences[idx],
                "sql": self.sqls[idx],
            }
            for rank, (template_score, semantic_score, lexical_score, _, idx) in enumerate(ranked[:k], start=1)
        ]


def masked_examples_equal(masked_target: str, example_question: str) -> bool:
    """Conservative runtime mask; place names are replaced for leakage checks."""
    regions = ("西湖区", "滨江区", "拱墅区", "上城区", "萧山区", "余杭区", "临平区", "钱塘区", "富阳区", "临安区", "桐庐县", "淳安县", "建德市")
    for region in regions:
        masked_target = masked_target.replace(region, "[LOC]")
    target = re.sub(r"\s+", "", masked_target)
    example = mask_question(example_question)
    for region in regions:
        example = example.replace(region, "[LOC]")
    return target == re.sub(r"\s+", "", example)

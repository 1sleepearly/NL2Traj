"""Assembly of the experimental NL2Traj prompt."""

from .prompt_components import (
    DDL_ONLY,
    POSTGIS_RAWDOCS,
    SHARED_TIME_CONVENTIONS,
    SPATIAL_SCHEMA_NOTES,
    examples_block,
    load_trajectory_knowledge,
    sql_output_contract,
)
from .light_template import extract_light_template, format_template_emphasis


def build_component_prompt(
    question: str,
    feedback: str = "",
    examples: str = "",
    *,
    include_knowledge: bool = True,
    include_context: bool = True,
) -> str:
    """Build Traj prompts from independently switchable ablation components.

    The always-on base contains the database schema, shared time conventions,
    neutral schema notes, and the SQL output contract.  ``knowledge`` owns the
    PostGIS/MobilityDB/trajectory-domain reference.  ``context`` owns retrieved
    demonstrations and the deterministic light-template emphasis.
    """
    feedback_block = f"/* Typed trajectory feedback */\n{feedback}\n\n" if feedback else ""
    knowledge_block = ""
    if include_knowledge:
        knowledge_block = f"""/* Static spatial knowledge used by NL2Traj */
{POSTGIS_RAWDOCS}

{load_trajectory_knowledge()}

"""
    context_block = ""
    if include_context:
        context_block = (
            examples_block(examples)
            + format_template_emphasis(extract_light_template(question))
        )
    return f"""{knowledge_block}
{SHARED_TIME_CONVENTIONS}

{context_block}
{DDL_ONLY}
{SPATIAL_SCHEMA_NOTES}
{feedback_block}
{sql_output_contract(question)}"""


def build_prompt(question: str, feedback: str = "", examples: str = "") -> str:
    return build_component_prompt(question, feedback=feedback, examples=examples)

"""
Judge Agent: Compare generated answer to reference and produce a comparison table and quality score (0-100).
"""

import os
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


class ComparisonRow(BaseModel):
    """One row of the comparison table."""

    criterion: str = Field(description="What is being compared (e.g. 'Fault_Active set', 'Routine cited')")
    in_reference: str = Field(description="How the reference answer addresses this (brief)")
    in_generated: str = Field(description="How the generated answer addresses this (brief)")
    match: str = Field(
        description="Yes, Partial, No, or Extra. Use Extra when the generated answer has accurate details beyond the reference."
    )


class JudgeResult(BaseModel):
    """Output of the Judge Agent."""

    comparison_table: list[ComparisonRow] = Field(
        description="Row per evaluation criterion: criterion, in_reference, in_generated, match"
    )
    score: int = Field(ge=0, le=100, description="Overall quality score 0-100")
    summary: str = Field(default="", description="One or two sentence summary of the evaluation")


@dataclass
class JudgeDeps:
    """Inputs for the judge."""

    question: str
    reference_answer: str
    generated_answer: str


# Model: use LLM from .env if set, else this default
JUDGE_MODEL = os.getenv("LLM", "openai:gpt-5.1")

_judge_agent: Agent[JudgeDeps, JudgeResult] | None = None


def _get_judge_agent() -> Agent[JudgeDeps, JudgeResult]:
    global _judge_agent
    if _judge_agent is None:
        agent = Agent[JudgeDeps, JudgeResult](
            JUDGE_MODEL,
            deps_type=JudgeDeps,
            output_type=JudgeResult,
        )

        @agent.instructions
        def add_context(ctx: RunContext[JudgeDeps]) -> str:
            return (
                "You are evaluating a generated answer against a reference answer for a PLC documentation question.\n\n"
                "Build a comparison table with one row per important criterion (e.g. key facts, routine names, conditions, "
                "consequences, sequence of steps). For each row set: criterion, in_reference (how reference addresses it), "
                "in_generated (how generated addresses it), match (Yes / Partial / No / Extra). "
                "Use Extra when the generated answer includes accurate details beyond the reference; extra accurate details "
                "should NOT reduce the score.\n\n"
                "Then assign an overall quality score from 0 to 100: 0 = wrong or missing, 100 = fully matches reference "
                "in content and key phrasing. Paraphrasing is acceptable; deduct only for missing or incorrect content. "
                "Extra accurate details in the generated answer do NOT hurt the score.\n\n"
                "Question:\n"
                f"{ctx.deps.question}\n\n"
                "Reference answer:\n"
                f"{ctx.deps.reference_answer}\n\n"
                "Generated answer:\n"
                f"{ctx.deps.generated_answer}"
            )

        _judge_agent = agent
    return _judge_agent


def run_judge(question: str, reference_answer: str, generated_answer: str) -> JudgeResult:
    """Run the judge to compare generated answer to reference; returns comparison table and score 0-100."""
    deps = JudgeDeps(
        question=question,
        reference_answer=reference_answer,
        generated_answer=generated_answer,
    )
    agent = _get_judge_agent()
    result = agent.run_sync(
        "Evaluate the generated answer against the reference. Output the comparison_table and score (0-100).",
        deps=deps,
    )
    return result.output


def format_judge_result(result: JudgeResult, max_cell: int = 60) -> str:
    """Format JudgeResult as a readable table and score for console output."""
    def _cell(s: str, w: int) -> str:
        if len(s) <= w:
            return s
        return s[: w - 1] + "…"

    lines = ["--- Judge evaluation ---", f"Score: {result.score}/100", ""]
    if result.summary:
        lines.append(f"Summary: {result.summary}\n")
    rows = result.comparison_table
    if not rows:
        return "\n".join(lines)
    col_criterion = "Criterion"
    col_ref = "In Reference"
    col_gen = "In Generated"
    col_match = "Match"
    w_c = max(len(col_criterion), min(max_cell, max((len(r.criterion) for r in rows), default=0)))
    w_r = max(len(col_ref), min(max_cell, max((len(r.in_reference) for r in rows), default=0)))
    w_g = max(len(col_gen), min(max_cell, max((len(r.in_generated) for r in rows), default=0)))
    w_m = max(len(col_match), 7)
    fmt = f"  {{:<{w_c}}}  {{:<{w_r}}}  {{:<{w_g}}}  {{:<{w_m}}}"
    lines.append(fmt.format(col_criterion, col_ref, col_gen, col_match))
    lines.append("-" * (w_c + w_r + w_g + w_m + 8))
    for row in rows:
        lines.append(fmt.format(_cell(row.criterion, w_c), _cell(row.in_reference, w_r), _cell(row.in_generated, w_g), row.match))
    return "\n".join(lines)

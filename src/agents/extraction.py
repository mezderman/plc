"""
Extraction Agent (LLM #1): Convert question → structured intent + resolved tags.

Input: question, tags.md text (via TagIndex)
Output: intent, resolved_tags (inputs, outputs, states, actions)
Post-process: verify every tag exists in TagIndex, drop unknown ones.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from ingestion.tag_index import TagIndex, load_tag_index


class ResolvedTags(BaseModel):
    """Tag names extracted from the question, grouped by role."""

    inputs: list[str] = Field(default_factory=list, description="Input tags (sensors, buttons, etc.)")
    outputs: list[str] = Field(default_factory=list, description="Output tags (actuators, lights, etc.)")
    states: list[str] = Field(default_factory=list, description="Internal state tags")
    actions: list[str] = Field(default_factory=list, description="Action-related tags")


class ExtractionResult(BaseModel):
    """Strict JSON output from the Extraction Agent."""

    intent: str = Field(description="Brief intent classification, e.g. TAG_LOOKUP, INDICATOR_STATE_QUERY, FAULT_RESET")
    resolved_tags: ResolvedTags = Field(default_factory=ResolvedTags)
    unknown_terms: list[str] = Field(default_factory=list, description="Terms mentioned but not in TagIndex")


@dataclass
class ExtractionDeps:
    """Dependencies for the extraction agent."""

    tag_index: TagIndex
    tags_md_text: str


def _build_system_prompt(tags_md: str) -> str:
    return f"""You are an extraction agent for a PLC (Programmable Logic Controller) system.
Given a user question about the PLC, extract:
1. intent: A brief classification. Use TAG_LOOKUP when the answer should come from the tag/reference documentation: e.g. what a tag or sensor does ("What does PhotoEye_Fill do?"), or what fault codes mean ("What are all the fault codes and what do they mean?"), or any question asking for a definition or list defined in the docs. Use ROUTINE_EXPLANATION for how/why something works or "what happens when [single event]?" (e.g. "Why can't you extend the seal cylinder...?", "What happens when the emergency stop is pressed?"—single trigger, one routine, short prose answer). Use PROCESS_FLOW only when the user explicitly asks for a walk-through or step-by-step sequence ("Walk me through...", "Step by step...") OR when the question is about a multi-step workflow with many sequential stages (e.g. "What happens when a box arrives at the fill station?"—full cycle: photoeye, latch, fill, level, delay, conveyor). Do NOT use PROCESS_FLOW for simple single-event questions like "What happens when E-stop is pressed?"—use ROUTINE_EXPLANATION. Use CONDITION_LIST when the user asks what conditions or requirements must be true for something to happen (e.g. "What conditions must be true for the conveyor to run?"). Use TROUBLESHOOTING only when the user describes a problem and asks what to check or how to fix it. Other options: INDICATOR_STATE_QUERY, FAULT_RESET.
2. resolved_tags: PLC tag names mentioned or implied, grouped into inputs, outputs, states, actions.
   - inputs: sensors, buttons, switches (e.g. PhotoEye_Fill, HMI_Start_Button)
   - outputs: actuators, lights, valves (e.g. Conveyor_Run, Stack_Light_Red)
   - states: internal flags (e.g. Fault_Active, Line_Running)
   - actions: tags related to actions (can overlap with above)
   - For fault or failure scenarios (timeout, rejected item, "what happens when X goes wrong?"): include tags for fault state, fault indication (e.g. stack light), and fault reset so retrieval captures the full fault response.

CRITICAL: Only output tag names that appear in the tags reference below. Use exact spelling.
If a term is not in the reference, put it in unknown_terms and do NOT add it to resolved_tags.

Tags reference (valid tag names and descriptions; may be JSON or markdown):
---
{tags_md}
---
"""


# Model: use LLM from .env if set, else this default
EXTRACTION_MODEL = os.getenv("LLM", "openai:gpt-5.1")

_extraction_agent: Agent[ExtractionDeps, ExtractionResult] | None = None


def _get_extraction_agent() -> Agent[ExtractionDeps, ExtractionResult]:
    global _extraction_agent
    if _extraction_agent is None:
        agent = Agent[ExtractionDeps, ExtractionResult](
            EXTRACTION_MODEL,
            deps_type=ExtractionDeps,
            output_type=ExtractionResult,
        )

        @agent.instructions
        def add_tags_context(ctx: RunContext[ExtractionDeps]) -> str:
            """Inject tags.md content into the prompt."""
            return _build_system_prompt(ctx.deps.tags_md_text)

        _extraction_agent = agent
    return _extraction_agent


def _filter_valid_tags(tag_names: list[str], tag_index: TagIndex) -> tuple[list[str], list[str]]:
    """Keep only tags that exist in TagIndex. Return (valid, unknown)."""
    valid = []
    unknown = []
    for name in tag_names:
        if name in tag_index:
            valid.append(name)
        else:
            unknown.append(name)
    return valid, unknown


def _validate_and_filter(result: ExtractionResult, tag_index: TagIndex) -> ExtractionResult:
    """Drop unknown tags from resolved_tags, add them to unknown_terms."""
    all_unknown = list(result.unknown_terms)

    for field in ("inputs", "outputs", "states", "actions"):
        tags = getattr(result.resolved_tags, field)
        valid, unknown = _filter_valid_tags(tags, tag_index)
        setattr(result.resolved_tags, field, valid)
        all_unknown.extend(unknown)

    result.unknown_terms = list(dict.fromkeys(all_unknown))  # dedupe, preserve order
    return result


# Default path for tags context sent to the LLM (ingested index from run_ingestion.py)
DEFAULT_TAGS_SOURCE = Path("data/tag_index.json")


def run_extraction(question: str, tag_index: TagIndex, tags_source_path: Path | str | None = None) -> ExtractionResult:
    """
    Run the extraction agent on a question.

    Args:
        question: User's question about the PLC
        tag_index: Loaded TagIndex (for validation)
        tags_source_path: Path to tags context for the LLM (JSON or markdown).
            If None, uses data/tag_index.json (run ingestion first).

    Returns:
        ExtractionResult with intent, resolved_tags (validated), unknown_terms
    """
    path = Path(tags_source_path) if tags_source_path else DEFAULT_TAGS_SOURCE
    tags_context_text = path.read_text(encoding="utf-8")

    deps = ExtractionDeps(tag_index=tag_index, tags_md_text=tags_context_text)
    agent = _get_extraction_agent()
    run_result = agent.run_sync(question, deps=deps)

    result = run_result.output
    return _validate_and_filter(result, tag_index)

"""
Final Answer Agent (LLM #3): Produce answer from selected blocks and main callees context.

Input: question, selected blocks, main callees, optional tag index for tag context.
Instructions: Answer only from provided blocks. Cite routine names.
"""

import os
import re
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from ingestion.tag_index import TagIndex
from tools.grep import BlockCandidate
from tools.call_graph_builder import MainCalleesContext


@dataclass
class AnswerComposerDeps:
    """Dependencies for the answer composer."""

    question: str
    blocks_text: str  # Formatted selected blocks with routine names and code
    paths_summary: str  # Execution paths (e.g. "fault: MainRoutine → ...")
    tag_context: str = ""  # Tag names and descriptions for tags referenced in blocks
    intent: str = ""  # e.g. TAG_LOOKUP, ROUTINE_EXPLANATION; used to tailor answer style


# Model: use LLM from .env if set, else this default
ANSWER_MODEL = os.getenv("LLM", "openai:gpt-5.1")

_answer_agent: Agent[AnswerComposerDeps, str] | None = None


def _get_answer_agent() -> Agent[AnswerComposerDeps, str]:
    global _answer_agent
    if _answer_agent is None:
        agent = Agent[AnswerComposerDeps, str](
            ANSWER_MODEL,
            deps_type=AnswerComposerDeps,
            output_type=str,
        )

        @agent.instructions
        def add_evidence(ctx: RunContext[AnswerComposerDeps]) -> str:
            tag_section = (
                f"Tag definitions (for context, e.g. timer presets):\n{ctx.deps.tag_context}\n\n"
                if ctx.deps.tag_context.strip()
                else ""
            )
            intent_guidance = ""
            if ctx.deps.intent.strip().upper() == "TAG_LOOKUP":
                intent_guidance = (
                    "This is a TAG_LOOKUP question: the user wants a short definition of a tag/sensor/device. "
                    "Answer from the Tag definitions above: what the tag is (type, location if given), and what it does (e.g. outputs TRUE when ...). "
                    "Keep the answer to one or two sentences; do not add routine logic or code detail unless the question asks for it.\n\n"
                )
            elif ctx.deps.intent.strip().upper() == "PROCESS_FLOW":
                intent_guidance = (
                    "This is a PROCESS_FLOW question: the user wants a step-by-step walk-through of what happens. "
                    "Use a numbered list (1. 2. 3. ...) with one step per line. Each step: what happens (trigger, action, or state change) and which tags are involved. "
                    "Keep each step concise—one line. Follow the actual sequence from the evidence (sensors, timers, outputs, in order).\n\n"
                )
            elif ctx.deps.intent.strip().upper() == "CONDITION_LIST":
                intent_guidance = (
                    "This is a CONDITION_LIST question: the user wants the list of conditions that must be true. "
                    "Use a concise numbered list (1. ... 2. ...). Each item: condition/tag + must be VALUE + brief parenthetical in one line (e.g. 'Line_Running must be TRUE (operator has pressed start)'). "
                    "Start with a brief intro like 'All of the following must be true:'. One line per item; no long paragraphs.\n\n"
                )
            elif ctx.deps.intent.strip().upper() == "TROUBLESHOOTING":
                intent_guidance = (
                    "This is a TROUBLESHOOTING question: the user wants to know what to check or how to fix a problem. "
                    "Use a concise numbered checklist format (1. ... 2. ...). Keep each list item short—one check or action and its key implication, in one or two sentences max. "
                    "When fault checks are relevant: name both Fault_Active and Fault_Code, and include specific fault code values from the evidence (e.g. code 1, code 2) with their causes. "
                    "Cover all blocking conditions from the evidence—including mode (manual vs auto) when it determines which routine runs.\n\n"
                )
            return (
                intent_guidance
                + "Answer only from the provided code blocks and tag definitions. Do not add information from outside the evidence.\n\n"
                "Be concise. Aim for 2–4 tight sentences for simple explanations; only use multiple paragraphs when the topic genuinely requires it. "
                "State each fact once—do not restate the same point in different words (e.g. avoid 'In plain terms...', 'So as long as...', 'Only if...'). "
                "Write in a conversational, helpful tone—as if explaining to an operator or colleague. "
                "Use plain language instead of code syntax; explain technical terms in human terms. When referring to Boolean values, write TRUE and FALSE in all caps. "
                "Describe outcomes from a human perspective (what happens), not assignment syntax. Cite routine names when helpful; avoid line numbers. "
                "Include the key logic (what condition allows/blocks the action), the tags involved, and when relevant the consequence (safety, damage). "
                "Include numeric values from the evidence when relevant (timer presets, delays).\n\n"
                f"{ctx.deps.paths_summary}\n\n"
                f"{tag_section}"
                "Evidence (selected code blocks):\n"
                f"{ctx.deps.blocks_text}"
            )

        _answer_agent = agent
    return _answer_agent


def _format_blocks(blocks: list[BlockCandidate]) -> str:
    """Format selected blocks for the LLM: routine name and block text."""
    parts = []
    for c in blocks:
        parts.append(f"[{c.routine_name}] (line {c.line_hit})\n{c.block_text}")
    return "\n\n---\n\n".join(parts)


def _build_tag_context(tag_index: TagIndex, blocks: list[BlockCandidate]) -> str:
    """Build a short tag-context string for tags that appear in the given blocks."""
    combined_text = "\n".join(c.block_text for c in blocks)
    lines = []
    for tag_name in sorted(tag_index.keys()):
        if re.search(r"\b" + re.escape(tag_name) + r"\b", combined_text):
            entry = tag_index.get(tag_name)
            if entry:
                lines.append(f"  {tag_name}: {entry.type} — {entry.description}")
    if not lines:
        return ""
    return "\n".join(lines)


def _format_paths(main_callees: MainCalleesContext) -> str:
    """Format execution paths for context."""
    if not main_callees.paths:
        return "No path information."
    lines = []
    for label, path in zip(main_callees.path_labels, main_callees.paths):
        lines.append(f"  {label}: {' → '.join(path)}")
    return "Execution paths (routine order):\n" + "\n".join(lines)


def run_answer_composer(
    question: str,
    selected_blocks: list[BlockCandidate],
    main_callees: MainCalleesContext,
    tag_index: TagIndex | None = None,
    intent: str = "",
) -> str:
    """
    Generate the final answer from selected blocks and main callees context.

    If tag_index is provided, tag definitions for tags referenced in the blocks
    are included. If intent is TAG_LOOKUP, answer is kept to a short tag definition.
    """
    if not selected_blocks:
        return "No relevant code blocks were selected to answer this question."

    blocks_text = _format_blocks(selected_blocks)
    paths_summary = _format_paths(main_callees)
    tag_context = _build_tag_context(tag_index, selected_blocks) if tag_index else ""

    deps = AnswerComposerDeps(
        question=question,
        blocks_text=blocks_text,
        paths_summary=paths_summary,
        tag_context=tag_context,
        intent=intent,
    )

    agent = _get_answer_agent()
    result = agent.run_sync(
        f"Question: {question}\n\nAnswer conversationally from the evidence below. Be helpful and use plain language.",
        deps=deps,
    )

    return result.output

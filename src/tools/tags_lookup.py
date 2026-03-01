"""
tags_lookup: For TAG_LOOKUP intent, get evidence from the tag index (and tags.md sections like Fault Codes).

Input: question, ExtractionResult, TagIndex, optional path to tags.md.
Output: formatted string (tag definitions + Fault Codes table when relevant).
Used by the pipeline instead of grep when intent is TAG_LOOKUP.
"""

import re
from pathlib import Path

from agents.extraction import ExtractionResult
from ingestion.tag_index import TagIndex


def _fault_codes_section_from_tags_md(path: Path) -> str:
    """Extract the ## Fault Codes section from tags.md. Returns empty string if not found."""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"## Fault Codes\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def _is_fault_codes_question(question: str) -> bool:
    """True if the question is asking for fault code definitions/list."""
    q = question.lower()
    return "fault code" in q and ("all" in q or "mean" in q or "what are" in q or "list" in q)


def tags_lookup(
    question: str,
    extraction: ExtractionResult,
    tag_index: TagIndex,
    tags_md_path: Path | str | None = None,
) -> str:
    """
    Build evidence string from the tag index for resolved tags.
    When the question is about fault codes, append the Fault Codes table from tags.md.
    """
    parts: list[str] = []

    # All resolved tag names
    rt = extraction.resolved_tags
    tag_names: list[str] = list(dict.fromkeys(rt.inputs + rt.outputs + rt.states + rt.actions))

    if tag_names:
        parts.append("Tag definitions (from tag index):")
        for name in sorted(tag_names):
            entry = tag_index.get(name)
            if entry:
                parts.append(f"  {name}: {entry.type} — {entry.description}")
        parts.append("")

    # If question is about fault codes, add the Fault Codes table from tags.md
    if tags_md_path and _is_fault_codes_question(question):
        path = Path(tags_md_path)
        fault_table = _fault_codes_section_from_tags_md(path)
        if fault_table:
            parts.append("Fault Codes (from tags.md):")
            parts.append(fault_table)

    return "\n".join(parts).strip() if parts else "No tag definitions found."

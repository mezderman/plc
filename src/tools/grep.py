"""
grep: Deterministic retrieval over routines.md.

Input: ExtractionResult from extraction agent.
Iterate over all tags in resolved_tags, search routines for each.
For each hit: extract enclosing IF/CASE block, store as candidate.
No filtering.
"""

import re
from pathlib import Path

from pydantic import BaseModel, Field

# Import ExtractionResult - use string to avoid circular import at module load
# We'll import at runtime or use TYPE_CHECKING
from agents.extraction import ExtractionResult


class BlockCandidate(BaseModel):
    """A candidate code block containing a tag hit."""

    block_id: str = Field(description="Unique ID, e.g. B1, B2")
    routine_name: str = Field(description="Routine where block was found")
    line_hit: int = Field(description="1-based line number where tag was found")
    line_start: int = Field(description="1-based start of enclosing block")
    line_end: int = Field(description="1-based end of enclosing block")
    block_text: str = Field(description="Full text of the enclosing block")
    tag: str = Field(description="Tag that was matched")


def _parse_routines(path: Path) -> dict[str, list[str]]:
    """Parse routines.md into routine_name -> list of code lines (1-based indexing for display)."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    routines: dict[str, list[str]] = {}
    i = 0

    while i < len(lines):
        line = lines[i]
        if re.match(r"^## \w+", line.strip()):
            routine_name = line.replace("##", "").strip()
            i += 1
            # Skip description, Called By, Calls, blank lines until ```
            while i < len(lines) and "```" not in lines[i]:
                i += 1
            if i < len(lines) and "```" in lines[i]:
                i += 1  # skip opening ```
                code_lines: list[str] = []
                while i < len(lines) and "```" not in lines[i]:
                    code_lines.append(lines[i])
                    i += 1
                if code_lines:
                    routines[routine_name] = code_lines
            continue
        i += 1

    return routines


def _extract_block(lines: list[str], hit_index: int) -> tuple[int, int, str] | None:
    """
    Extract the enclosing IF...END IF or CASE...END CASE block around line hit_index.
    hit_index is 0-based into lines.
    Returns (start_index, end_index, block_text) or None.
    """
    if hit_index < 0 or hit_index >= len(lines):
        return None

    # Find the innermost IF that contains hit_index
    # Scan backward to find IF lines before hit_index
    if_starts: list[int] = []
    for i in range(hit_index + 1):
        stripped = lines[i].strip()
        if re.match(r"^IF\s+", stripped, re.IGNORECASE) or re.match(r"^IF\s+", stripped):
            if_starts.append(i)
        elif re.match(r"^CASE\s+", stripped, re.IGNORECASE):
            if_starts.append(i)

    if not if_starts:
        # No IF/CASE before hit - return the hit line as minimal block
        return (hit_index, hit_index, lines[hit_index])

    # Start from the last (innermost) IF before hit
    start = if_starts[-1]
    depth = 0
    end = start

    for i in range(start, len(lines)):
        stripped = lines[i].strip()
        if re.match(r"^IF\s+", stripped) or re.match(r"^CASE\s+", stripped):
            depth += 1
        if re.match(r"^END\s+IF", stripped, re.IGNORECASE) or re.match(r"^END\s+CASE", stripped, re.IGNORECASE):
            depth -= 1
            if depth == 0:
                end = i
                break

    if depth != 0:
        # Unclosed block - return from start to end of routine
        end = len(lines) - 1

    block_text = "\n".join(lines[start : end + 1])
    return (start, end, block_text)


def _tag_matches_line(tag: str, line: str) -> bool:
    """Check if tag appears as a whole word in line (avoid partial matches like Fill in Fill_Valve when searching Fill)."""
    # Use word boundary: tag should not be part of a larger identifier
    # e.g. "Stack_Light_Yellow" matches "Stack_Light_Yellow :="
    # "Fill" should match "Fill_Valve" when we search "Fill"? No - we search exact tag names.
    # Tags are like PhotoEye_Fill, HMI_Manual_Mode - we want exact match
    pattern = r"\b" + re.escape(tag) + r"\b"
    return bool(re.search(pattern, line))


def grep_tags(extraction_result: ExtractionResult, routines_path: Path | str) -> list[BlockCandidate]:
    """
    Retrieval (deterministic): search routines for all tags in extraction result.

    For each tag in resolved_tags (inputs, outputs, states, actions):
    - Search all routines for that string
    - For each hit: extract enclosing block
    - Store as candidate (no filtering)

    Returns list of BlockCandidate.
    """
    path = Path(routines_path)
    routines = _parse_routines(path)

    # Collect all tags from extraction result
    tags: set[str] = set()
    rt = extraction_result.resolved_tags
    for name in rt.inputs + rt.outputs + rt.states + rt.actions:
        tags.add(name)

    candidates: list[BlockCandidate] = []
    block_counter = 0

    for routine_name, code_lines in routines.items():
        for hit_idx, line in enumerate(code_lines):
            for tag in tags:
                if _tag_matches_line(tag, line):
                    block_result = _extract_block(code_lines, hit_idx)
                    if block_result:
                        line_start, line_end, block_text = block_result
                        block_counter += 1
                        block_id = f"B{block_counter}"
                        candidates.append(
                            BlockCandidate(
                                block_id=block_id,
                                routine_name=routine_name,
                                line_hit=hit_idx + 1,  # 1-based
                                line_start=line_start + 1,  # 1-based
                                line_end=line_end + 1,  # 1-based
                                block_text=block_text,
                                tag=tag,
                            )
                        )

    return candidates

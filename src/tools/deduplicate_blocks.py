"""
deduplicate_blocks: Remove duplicate blocks from grep output.

Blocks are considered duplicates when they have the same routine_name and block_text.
Keeps the first occurrence, reassigns sequential block IDs (B1, B2, ...).
"""

from tools.grep import BlockCandidate


def deduplicate_blocks(candidates: list[BlockCandidate]) -> list[BlockCandidate]:
    """
    Deduplicate by (routine_name, block_text). Preserve first occurrence order.
    Reassign block_id to B1, B2, ... for a clean sequential sequence.
    """
    seen: dict[tuple[str, str], BlockCandidate] = {}
    for c in candidates:
        key = (c.routine_name, c.block_text)
        if key not in seen:
            seen[key] = c

    result: list[BlockCandidate] = []
    for i, c in enumerate(seen.values(), start=1):
        result.append(
            BlockCandidate(
                block_id=f"B{i}",
                routine_name=c.routine_name,
                line_hit=c.line_hit,
                line_start=c.line_start,
                line_end=c.line_end,
                block_text=c.block_text,
                tag=c.tag,
            )
        )
    return result

"""
Call graph builder (deterministic): MainRoutine + routines it calls.

Parses routines.md, extracts MainRoutine and every "Call X". Builds each possible
execution path as an ordered list of routine names. Static per project.
"""

import re
from pathlib import Path

from pydantic import BaseModel, Field


class MainCalleesContext(BaseModel):
    """MainRoutine plus the list of routines it calls, and each possible path in order."""

    routines: list[str] = Field(
        default_factory=list,
        description="MainRoutine + routines it calls (order of first Call).",
    )
    main_routine_code: str = Field(
        default="",
        description="Full MainRoutine code block.",
    )
    paths: list[list[str]] = Field(
        default_factory=list,
        description="Each possible execution path: ordered list of routine names.",
    )
    path_labels: list[str] = Field(
        default_factory=list,
        description="Optional label per path, e.g. fault, manual, auto.",
    )
    notes: list[str] = Field(default_factory=list, description="Optional notes.")


def _parse_routines(path: Path) -> dict[str, list[str]]:
    """Parse routines.md into routine_name -> list of code lines."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    routines: dict[str, list[str]] = {}
    i = 0

    while i < len(lines):
        line = lines[i]
        if re.match(r"^## \w+", line.strip()):
            routine_name = line.replace("##", "").strip()
            i += 1
            while i < len(lines) and "```" not in lines[i]:
                i += 1
            if i < len(lines) and "```" in lines[i]:
                i += 1
                code_lines: list[str] = []
                while i < len(lines) and "```" not in lines[i]:
                    code_lines.append(lines[i])
                    i += 1
                if code_lines:
                    routines[routine_name] = code_lines
            continue
        i += 1

    return routines


def _extract_called_routines(code_lines: list[str]) -> list[str]:
    """Extract routine names from 'Call RoutineName' lines. Preserve order, unique."""
    seen: set[str] = set()
    result: list[str] = []
    for line in code_lines:
        m = re.search(r"\bCall\s+(\w+)", line, re.IGNORECASE)
        if m:
            name = m.group(1)
            if name not in seen:
                seen.add(name)
                result.append(name)
    return result


def _extract_calls_in_order(lines: list[str]) -> list[str]:
    """Extract all 'Call X' in order (non-unique)."""
    result: list[str] = []
    for line in lines:
        m = re.search(r"\bCall\s+(\w+)", line, re.IGNORECASE)
        if m:
            result.append(m.group(1))
    return result


def _find_matching_end_if(lines: list[str], if_start: int) -> int:
    """Return the index of the END IF that matches the IF at if_start. Depth-counting."""
    depth = 0
    for i in range(if_start, len(lines)):
        stripped = lines[i].strip()
        if re.match(r"^IF\s+", stripped) or re.match(r"^CASE\s+", stripped):
            depth += 1
        if re.match(r"^END\s+IF", stripped, re.IGNORECASE) or re.match(r"^END\s+CASE", stripped, re.IGNORECASE):
            depth -= 1
            if depth == 0:
                return i
    return -1


def _find_else(lines: list[str], if_start: int, end_if_idx: int) -> int:
    """Return index of ELSE between if_start and end_if_idx at same depth, or -1."""
    depth = 0
    for i in range(if_start + 1, end_if_idx):
        stripped = lines[i].strip()
        if re.match(r"^IF\s+", stripped):
            depth += 1
        if re.match(r"^END\s+IF", stripped, re.IGNORECASE):
            depth -= 1
        if depth == 0 and re.match(r"^ELSE\s*$", stripped, re.IGNORECASE):
            return i
    return -1


def _build_paths_from_main(main_lines: list[str]) -> tuple[list[list[str]], list[str]]:
    """
    Parse MainRoutine control flow and return (paths, path_labels).
    Assumes: optional prefix calls, then IF Fault_Active THEN ... END IF, then IF HMI_Manual_Mode THEN ... ELSE ... END IF, then trailing calls.
    """
    paths: list[list[str]] = []
    path_labels: list[str] = []
    MAIN = "MainRoutine"

    i = 0
    # Unconditional prefix (until first IF)
    prefix_calls: list[str] = []
    while i < len(main_lines):
        line = main_lines[i]
        if re.match(r"^\s*IF\s+", line.strip()):
            break
        m = re.search(r"\bCall\s+(\w+)", line, re.IGNORECASE)
        if m:
            prefix_calls.append(m.group(1))
        i += 1

    if i >= len(main_lines):
        # No IF found, single path
        path = [MAIN] + prefix_calls
        return [path], ["default"]

    # First IF (Fault_Active)
    if_start = i
    end_if = _find_matching_end_if(main_lines, if_start)
    if end_if < 0:
        return [([MAIN] + prefix_calls)], ["default"]

    then_block = main_lines[if_start + 1 : end_if]
    fault_calls = _extract_calls_in_order(then_block)
    paths.append([MAIN] + prefix_calls + fault_calls)
    path_labels.append("fault")

    # Rest after first END IF
    i = end_if + 1
    rest = main_lines[i:] if i < len(main_lines) else []

    # Second IF (HMI_Manual_Mode) THEN ... ELSE ... END IF
    j = 0
    while j < len(rest) and not re.match(r"^\s*IF\s+", rest[j].strip()):
        j += 1
    if j >= len(rest):
        return paths, path_labels

    if_start2 = j
    end_if2 = _find_matching_end_if(rest, if_start2)
    if end_if2 < 0:
        return paths, path_labels

    else_idx = _find_else(rest, if_start2, end_if2)
    if else_idx < 0:
        # No ELSE: one branch
        then_block2 = rest[if_start2 + 1 : end_if2]
        then_calls = _extract_calls_in_order(then_block2)
        after = rest[end_if2 + 1 :]
        after_calls = _extract_calls_in_order(after)
        path = [MAIN] + prefix_calls + then_calls + after_calls
        paths.append(path)
        path_labels.append("manual")
        return paths, path_labels

    then_block2 = rest[if_start2 + 1 : else_idx]
    else_block2 = rest[else_idx + 1 : end_if2]
    after = rest[end_if2 + 1 :]
    after_calls = _extract_calls_in_order(after)

    then_calls = _extract_calls_in_order(then_block2)
    else_calls = _extract_calls_in_order(else_block2)

    paths.append([MAIN] + prefix_calls + then_calls + after_calls)
    path_labels.append("manual")
    paths.append([MAIN] + prefix_calls + else_calls + after_calls)
    path_labels.append("auto")

    return paths, path_labels


def build_main_callees(routines_path: Path | str) -> MainCalleesContext:
    """
    Build main callees context: MainRoutine + list of routines it calls.

    Static per routines.md. Does not depend on the question.
    """
    path = Path(routines_path)
    routines = _parse_routines(path)

    if "MainRoutine" not in routines:
        return MainCalleesContext(
            routines=[],
            main_routine_code="",
            paths=[],
            path_labels=[],
            notes=["MainRoutine not found."],
        )

    main_lines = routines["MainRoutine"]
    main_routine_code = "\n".join(main_lines)
    called = _extract_called_routines(main_lines)
    paths, path_labels = _build_paths_from_main(main_lines)

    return MainCalleesContext(
        routines=["MainRoutine"] + called,
        main_routine_code=main_routine_code,
        paths=paths,
        path_labels=path_labels,
        notes=[],
    )

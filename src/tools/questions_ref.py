"""Load question and reference answer pairs from questions.md for evaluation."""

import re
from pathlib import Path


def load_questions(path: Path | str) -> list[tuple[str, str]]:
    """
    Parse questions.md and return list of (question_text, reference_answer).
    Question text is the line after **Question:**; reference is after **Reference Answer:** until --- or next ##.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    # Sections start with ## Question N (Difficulty - Category)
    blocks = re.split(r"\n## Question \d+[^\n]*\n", text)
    results: list[tuple[str, str]] = []
    for block in blocks[1:]:  # skip content before first question
        q_match = re.search(
            r"\*\*Question:\*\*\s*(.+?)(?=\n\*\*Reference Answer:\*\*)",
            block,
            re.DOTALL,
        )
        ref_match = re.search(
            r"\*\*Reference Answer:\*\*\s*(.+?)(?=\n---|\n## Question |\n## Scoring|\Z)",
            block,
            re.DOTALL,
        )
        if q_match and ref_match:
            q = q_match.group(1).strip()
            ref = ref_match.group(1).strip()
            results.append((q, ref))
    return results


def get_question(path: Path | str, number: int) -> str | None:
    """
    Get question text by 1-based index (e.g. 1 = first question, 2 = second).
    Returns None if number is out of range.
    """
    pairs = load_questions(path)
    if number < 1 or number > len(pairs):
        return None
    return pairs[number - 1][0]


def find_reference(question: str, path: Path | str) -> str | None:
    """
    Find reference answer for a question by exact or normalized match.
    Returns reference text if found, else None.
    """
    pairs = load_questions(path)
    q_normalized = question.strip().lower()
    for q_text, ref_text in pairs:
        if q_text.strip().lower() == q_normalized:
            return ref_text
    # Substring fallback: if asked question contains a known question or vice versa
    for q_text, ref_text in pairs:
        q_ref_norm = q_text.strip().lower()
        if q_normalized in q_ref_norm or q_ref_norm in q_normalized:
            return ref_text
    return None

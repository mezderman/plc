"""Run extraction then grep: question number or text → extraction → grep → print candidates.

Usage:
    python scripts/run_grep.py
    python scripts/run_grep.py 5                    # question #5, default openai
    python scripts/run_grep.py 9 anthropic         # question #9, Anthropic
    python scripts/run_grep.py anthropic 9        # same: provider first
    python scripts/run_grep.py "What does PhotoEye_Fill do?"
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Parse args: support (question, provider) or (provider, question)
_valid_providers = ("openai", "anthropic")
_args = [a.strip().lower() for a in sys.argv[1:3] if len(sys.argv) > 1]
if len(_args) >= 2 and _args[0] in _valid_providers and _args[1] not in _valid_providers:
    _provider, _raw = _args[0], _args[1]
elif len(_args) >= 2 and _args[1] in _valid_providers:
    _raw, _provider = _args[0], _args[1]
elif len(_args) >= 1:
    _raw = _args[0]
    _provider = "openai"
else:
    _raw = input("Question or number (e.g. 2): ").strip()
    _provider = "openai"

# Set LLM before importing agents
if _provider == "anthropic":
    _model = os.environ.get("ANTHROPIC_MODEL")
    if not _model:
        print("Error: ANTHROPIC_MODEL is not set. Add it to .env for Anthropic.")
        sys.exit(1)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY is not set. Add it to .env (see .env.example)")
        sys.exit(1)
    if not _model.startswith("anthropic:"):
        _model = f"anthropic:{_model}"
    os.environ["LLM"] = _model
else:
    if _provider != "openai":
        print(f"Unknown provider '{_provider}', using openai.")
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set. Add it to .env (see .env.example)")
        sys.exit(1)
    os.environ["LLM"] = os.environ.get("OPENAI_MODEL", "openai:gpt-5.1")

from agents.extraction import run_extraction
from ingestion.tag_index import load_tag_index_from_json
from tools.deduplicate_blocks import deduplicate_blocks
from tools.grep import grep_tags
from tools.questions_ref import get_question

# ANSI colors for terminal output (disabled when stdout is not a TTY)
def _color(s: str, codes: str) -> str:
    return (codes + s + "\033[0m") if sys.stdout.isatty() else s


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    index_path = project_root / "data" / "tag_index.json"
    questions_path = project_root / "docs" / "questions.md"
    routines_path = project_root / "docs" / "routines.md"

    if not index_path.exists():
        print(f"Error: {index_path} not found. Run ingestion first.")
        sys.exit(1)
    if not routines_path.exists():
        print(f"Error: {routines_path} not found.")
        sys.exit(1)

    if not _raw:
        print("No question provided.")
        sys.exit(1)

    if _raw.isdigit():
        n = int(_raw)
        question = get_question(questions_path, n)
        if question is None:
            print(f"Error: Question #{n} not found. Check docs/questions.md (1–10).")
            sys.exit(1)
        print(f"Question #{n}: {question}\n")
    else:
        question = _raw

    print(f"Model: {os.environ.get('LLM', 'openai:gpt-5.1')}\n", flush=True)

    # 1. Run extraction (same as run_extraction)
    tag_index = load_tag_index_from_json(index_path)
    extraction_result = run_extraction(question, tag_index, tags_source_path=index_path)

    print("--- Extraction ---")
    print(f"Intent: {extraction_result.intent}")
    print(f"Resolved tags: inputs={extraction_result.resolved_tags.inputs}, "
          f"outputs={extraction_result.resolved_tags.outputs}, "
          f"states={extraction_result.resolved_tags.states}, "
          f"actions={extraction_result.resolved_tags.actions}")
    if extraction_result.unknown_terms:
        print(f"Unknown terms: {extraction_result.unknown_terms}")

    # 2. Grep using extraction result
    candidates_raw = grep_tags(extraction_result, routines_path)

    print(f"\n--- Grep results ({len(candidates_raw)} blocks) ---")
    for c in candidates_raw:
        print(f"\n[{c.block_id}] {c.routine_name} line {c.line_hit} (tag: {c.tag})")
        print(f"  Block lines {c.line_start}-{c.line_end}:")
        for i, line in enumerate(c.block_text.splitlines(), start=c.line_start):
            print(f"    {i:3}: {line}")

    # 3. Deduplicate, print final candidates
    candidates = deduplicate_blocks(candidates_raw)
    sep = "=" * 60
    print(_color(f"\n{sep}\n  After dedup: {len(candidates)} candidates (from {len(candidates_raw)} blocks)\n{sep}\n", "\033[1;36m"))
    for c in candidates:
        print(_color(f"[{c.block_id}] {c.routine_name} L{c.line_hit}", "\033[1;32m"))
        print(_color(f"  Block lines {c.line_start}-{c.line_end}:", "\033[2m"))
        for i, line in enumerate(c.block_text.splitlines(), start=c.line_start):
            print(_color(f"    {i:3}: {line}", "\033[2m"))
        print()


if __name__ == "__main__":
    main()

"""Test extraction + grep pipeline. User inputs question, prints extraction and candidates.

Usage:
    python test/grep_test.py
    python test/grep_test.py "What color is the stack light in manual mode?"
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Allow imports from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.extraction import run_extraction
from ingestion.tag_index import load_tag_index_from_json
from tools.grep import grep_tags


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set. Add it to .env (see .env.example)")
        sys.exit(1)

    project_root = Path(__file__).resolve().parent.parent
    index_path = project_root / "data" / "tag_index.json"
    routines_path = project_root / "docs" / "routines.md"

    if not index_path.exists():
        print(f"Error: {index_path} not found. Run ingestion first.")
        sys.exit(1)

    if not routines_path.exists():
        print(f"Error: {routines_path} not found.")
        sys.exit(1)

    question = sys.argv[1] if len(sys.argv) > 1 else input("Question: ").strip()
    if not question:
        print("No question provided.")
        sys.exit(1)

    tag_index = load_tag_index_from_json(index_path)
    extraction_result = run_extraction(question, tag_index)

    print("\n--- Extraction ---")
    print(f"Intent: {extraction_result.intent}")
    print(f"Resolved tags: inputs={extraction_result.resolved_tags.inputs}, "
          f"outputs={extraction_result.resolved_tags.outputs}, "
          f"states={extraction_result.resolved_tags.states}, "
          f"actions={extraction_result.resolved_tags.actions}")
    if extraction_result.unknown_terms:
        print(f"Unknown terms: {extraction_result.unknown_terms}")

    candidates = grep_tags(extraction_result, routines_path)

    print(f"\n--- Grep results ({len(candidates)} candidates) ---")
    for c in candidates:
        print(f"\n[{c.block_id}] {c.routine_name} line {c.line_hit} (tag: {c.tag})")
        print(f"  Block lines {c.line_start}-{c.line_end}:")
        for i, line in enumerate(c.block_text.splitlines(), start=c.line_start):
            print(f"    {i:3}: {line}")


if __name__ == "__main__":
    main()

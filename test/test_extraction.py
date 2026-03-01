"""Test the extraction agent. Prints ExtractionResult for a given question.

Usage:
    python test/test_extraction.py "What happens when the emergency stop is pressed?"
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Allow imports from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from agents.extraction import run_extraction
from ingestion.tag_index import load_tag_index_from_json


def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY is not set. Add it to .env (see .env.example)")
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Usage: python test/test_extraction.py \"<question>\"")
        sys.exit(1)

    question = sys.argv[1]
    index_path = Path(__file__).resolve().parent.parent / "data" / "tag_index.json"

    if not index_path.exists():
        print(f"Error: {index_path} not found. Run ingestion first.")
        sys.exit(1)

    tag_index = load_tag_index_from_json(index_path)
    result = run_extraction(question, tag_index)

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()

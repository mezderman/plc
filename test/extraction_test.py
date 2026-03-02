"""Run extraction agent in isolation. Prints ExtractionResult for a question.

Usage:
    python test/extraction_test.py
    python test/extraction_test.py 3                    # question #3, default openai
    python test/extraction_test.py 9 anthropic          # question #9, Anthropic
    python test/extraction_test.py anthropic 9          # same: provider first
    python test/extraction_test.py "What does PhotoEye_Fill do?"
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
from tools.questions_ref import get_question


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    index_path = project_root / "data" / "tag_index.json"
    questions_path = project_root / "docs" / "questions.md"

    if not index_path.exists():
        print(f"Error: {index_path} not found. Run ingestion first.")
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

    tag_index = load_tag_index_from_json(index_path)
    result = run_extraction(question, tag_index)

    print("--- Extraction ---")
    print(f"Intent: {result.intent}")
    print(f"Resolved tags: inputs={result.resolved_tags.inputs}, "
          f"outputs={result.resolved_tags.outputs}, "
          f"states={result.resolved_tags.states}, "
          f"actions={result.resolved_tags.actions}")
    if result.unknown_terms:
        print(f"Unknown terms: {result.unknown_terms}")


if __name__ == "__main__":
    main()

"""Run the full pipeline: question → extract → main_callees → grep/tags_lookup → answer → judge.

Usage:
    python test/run_pipeline.py
    python test/run_pipeline.py "What color is the stack light in manual mode?"
    python test/run_pipeline.py 2              # question #2, default openai
    python test/run_pipeline.py 9 anthropic   # question #9, Anthropic model
    python test/run_pipeline.py anthropic 9   # same: provider first, question second
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

# Set LLM before importing pipeline/agents so they pick up the chosen model
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

from pipeline import Pipeline
from agents.judge import format_judge_result
from tools.questions_ref import get_question


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    questions_path = project_root / "docs" / "questions.md"

    if not _raw:
        print("No question provided.")
        sys.exit(1)

    # If argument is a number, use that question from docs/questions.md
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

    def on_progress(stage: str, data) -> None:
        if stage == "extraction":
            ext = data
            print("\n--- Extraction ---", flush=True)
            print(f"Intent: {ext.intent}", flush=True)
            print(f"Resolved tags: {ext.resolved_tags}", flush=True)
            if ext.unknown_terms:
                print(f"Unknown terms: {ext.unknown_terms}", flush=True)
        elif stage == "main_callees":
            ctx = data
            print("\n--- Main callees (paths) ---", flush=True)
            for label, path in zip(ctx.path_labels, ctx.paths):
                print(f"  {label}: {' → '.join(path)}", flush=True)
        elif stage == "candidates":
            grep_count, candidates, selection = data
            if grep_count is not None:
                print(f"\nGrep retrieved: {grep_count} blocks", flush=True)
                print(f"After dedup: {len(candidates)} blocks", flush=True)
            else:
                print(f"\nBlocks: {len(candidates)} (TAG_LOOKUP)", flush=True)
            for c in candidates:
                print(f"\n[{c.block_id}] {c.routine_name} L{c.line_hit}", flush=True)
                for line in c.block_text.splitlines():
                    print(f"    {line}", flush=True)
        elif stage == "answer":
            print("\n--- Answer ---", flush=True)
            print(data, flush=True)
        elif stage == "judge":
            if data is not None:
                print("\n" + format_judge_result(data), flush=True)
            else:
                print("\n--- Judge ---", flush=True)
                print("No reference found in docs/questions.md for this question.", flush=True)

    pipeline = Pipeline(project_root)
    pipeline.run(question, on_progress=on_progress)


if __name__ == "__main__":
    main()

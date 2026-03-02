"""Run pipeline on all questions 1-10 and save judge evaluation report.

Usage:
    python scripts/run_evaluation.py openai
    python scripts/run_evaluation.py anthropic
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Set LLM before importing pipeline/agents
_provider = (sys.argv[1].lower() if len(sys.argv) > 1 else "openai").strip()
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
    _model = os.environ.get("OPENAI_MODEL", "openai:gpt-5.1")
    os.environ["LLM"] = _model

from pipeline import Pipeline
from agents.judge import format_judge_result
from tools.questions_ref import get_question


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    questions_path = project_root / "docs" / "questions.md"
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)

    pipeline = Pipeline(project_root)
    model_name = os.environ.get("LLM", _model)

    report_lines: list[str] = []
    report_lines.append(f"Model: {model_name}")
    report_lines.append("")

    for n in range(1, 11):
        question = get_question(questions_path, n)
        if question is None:
            report_lines.append(f"## Question {n}")
            report_lines.append("(not found)")
            report_lines.append("")
            continue

        print(f"Running question {n}...", flush=True)
        start = time.perf_counter()
        result = pipeline.run(question, on_progress=None)
        elapsed = time.perf_counter() - start

        report_lines.append(f"## Question {n}")
        report_lines.append(f"**Question:** {question.strip()}")
        report_lines.append(f"**Model:** {model_name}")
        report_lines.append(f"**Time:** {elapsed:.2f}s")
        report_lines.append("")
        report_lines.append("**Answer:**")
        report_lines.append(result.answer)
        report_lines.append("")

        if result.judge_result:
            report_lines.append(format_judge_result(result.judge_result))
        else:
            report_lines.append("--- Judge evaluation ---")
            report_lines.append("No reference found in questions.md for this question.")
        report_lines.append("")
        report_lines.append("---")

    report_text = "\n".join(report_lines)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    provider_slug = "openai" if "openai" in model_name.lower() else "anthropic"
    out_path = results_dir / f"eval_{provider_slug}_{timestamp}.txt"
    out_path.write_text(report_text, encoding="utf-8")
    print(f"\nReport saved to {out_path}")


if __name__ == "__main__":
    main()

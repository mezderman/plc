"""Build the call graph from docs/routines.md and print it (same step used in the pipeline).

Usage:
    python scripts/run_call_graph.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tools.call_graph_builder import build_main_callees


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    routines_path = project_root / "docs" / "routines.md"

    if not routines_path.exists():
        print(f"Error: {routines_path} not found.")
        sys.exit(1)

    ctx = build_main_callees(routines_path)

    print("--- Call graph (main callees) ---")
    print("Routines (callee list):", ctx.routines)
    print("Paths (each possible path in order):")
    for label, path in zip(ctx.path_labels, ctx.paths):
        print(f"  {label}: {' → '.join(path)}")
    code_preview = ctx.main_routine_code[:300] + "..." if len(ctx.main_routine_code) > 300 else ctx.main_routine_code
    print("Main routine code (preview):", code_preview)
    if ctx.notes:
        print("Notes:", ctx.notes)


if __name__ == "__main__":
    main()

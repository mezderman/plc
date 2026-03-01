"""Tests for call_graph_builder: build_main_callees and MainCalleesContext."""

import sys
from pathlib import Path

# Allow imports from src
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tools.call_graph_builder import MainCalleesContext, build_main_callees


def test_build_main_callees_with_routines_md() -> None:
    """With project docs/routines.md, MainRoutine exists: routines and main_routine_code are populated."""
    project_root = Path(__file__).resolve().parent.parent
    routines_path = project_root / "docs" / "routines.md"

    if not routines_path.exists():
        raise FileNotFoundError(f"Need {routines_path} to run this test")

    ctx = build_main_callees(routines_path)

    print("\n--- call_graph_builder output ---")
    print("routines (callee list):", ctx.routines)
    print("paths (each possible path in order):")
    for label, path in zip(ctx.path_labels, ctx.paths):
        print(f"  {label}: {' → '.join(path)}")
    print("main_routine_code (first 200 chars):", ctx.main_routine_code[:200] + "..." if len(ctx.main_routine_code) > 200 else ctx.main_routine_code)
    print("notes:", ctx.notes)
    print()

    assert isinstance(ctx, MainCalleesContext)
    assert ctx.routines[0] == "MainRoutine"
    assert "SafetyCheck" in ctx.routines
    assert "StackLightControl" in ctx.routines
    assert "ManualMode" in ctx.routines
    assert "AutoMode" in ctx.routines
    assert "FaultHandler" in ctx.routines
    assert len(ctx.routines) == 6

    assert len(ctx.paths) == 3
    assert ctx.path_labels == ["fault", "manual", "auto"]
    fault_path = ctx.paths[0]
    assert fault_path == ["MainRoutine", "SafetyCheck", "FaultHandler", "StackLightControl"]
    manual_path = ctx.paths[1]
    assert manual_path == ["MainRoutine", "SafetyCheck", "ManualMode", "StackLightControl"]
    auto_path = ctx.paths[2]
    assert auto_path == ["MainRoutine", "SafetyCheck", "AutoMode", "StackLightControl"]

    assert len(ctx.main_routine_code) > 0
    assert "Call SafetyCheck" in ctx.main_routine_code
    assert "IF Fault_Active" in ctx.main_routine_code
    assert "HMI_Manual_Mode" in ctx.main_routine_code

    assert ctx.notes == []


def test_build_main_callees_without_main_routine() -> None:
    """When MainRoutine is missing, routines and main_routine_code are empty, notes explain."""
    project_root = Path(__file__).resolve().parent.parent
    # Use a file that has no MainRoutine: e.g. docs/tags.md or a minimal temp
    other_path = project_root / "docs" / "tags.md"

    ctx = build_main_callees(other_path)

    assert ctx.routines == []
    assert ctx.main_routine_code == ""
    assert ctx.paths == []
    assert ctx.path_labels == []
    assert "MainRoutine not found" in ctx.notes[0]


def test_main_callees_context_model() -> None:
    """MainCalleesContext accepts routines, main_routine_code, paths, path_labels, notes."""
    ctx = MainCalleesContext(
        routines=["MainRoutine", "SafetyCheck"],
        main_routine_code="Call SafetyCheck",
        paths=[["MainRoutine", "SafetyCheck"]],
        path_labels=["default"],
        notes=[],
    )
    assert ctx.routines == ["MainRoutine", "SafetyCheck"]
    assert ctx.main_routine_code == "Call SafetyCheck"
    assert ctx.paths == [["MainRoutine", "SafetyCheck"]]
    assert ctx.path_labels == ["default"]
    assert ctx.notes == []


if __name__ == "__main__":
    test_build_main_callees_with_routines_md()
    test_build_main_callees_without_main_routine()
    test_main_callees_context_model()
    print("All tests passed.")

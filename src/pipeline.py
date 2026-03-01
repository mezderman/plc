"""
Main pipeline: question → extract → main_callees → grep/tags_lookup → answer → judge.

Single entry point for the full workflow.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from agents.answer_composer import run_answer_composer
from agents.extraction import ExtractionResult, run_extraction
from agents.judge import JudgeResult, format_judge_result, run_judge
from ingestion.tag_index import TagIndex, load_tag_index_from_json
from tools.grep import BlockCandidate, grep_tags
from tools.call_graph_builder import MainCalleesContext, build_main_callees
from tools.questions_ref import find_reference
from tools.tags_lookup import tags_lookup
from tools.deduplicate_blocks import deduplicate_blocks


@dataclass
class BlockSelectionResult:
    """Selected block IDs passed to the answer composer (all candidates when no selector)."""

    selected_block_ids: list[str]


@dataclass
class PipelineResult:
    """Result of running the pipeline on a question."""

    question: str
    extraction: ExtractionResult
    main_callees: MainCalleesContext
    candidates: list[BlockCandidate]
    selection: BlockSelectionResult
    answer: str = ""
    judge_result: JudgeResult | None = None  # Set when reference exists and judge runs


class Pipeline:
    """
    Runs the full workflow: extract → main_callees → grep/tags_lookup → answer → judge.

    Paths are relative to project_root if not absolute.
    """

    def __init__(
        self,
        project_root: Path | str,
        *,
        tag_index_path: Path | str | None = None,
        routines_path: Path | str | None = None,
        tags_source_path: Path | str | None = None,
        questions_path: Path | str | None = None,
    ):
        self.project_root = Path(project_root)
        self._tag_index_path = Path(tag_index_path) if tag_index_path else self.project_root / "data" / "tag_index.json"
        self._routines_path = Path(routines_path) if routines_path else self.project_root / "docs" / "routines.md"
        self._tags_source_path = Path(tags_source_path) if tags_source_path else self.project_root / "data" / "tag_index.json"
        self._questions_path = Path(questions_path) if questions_path else self.project_root / "docs" / "questions.md"
        self._tags_md_path = self.project_root / "docs" / "tags.md"

        self._tag_index: TagIndex | None = None
        self._main_callees: MainCalleesContext | None = None

    def _get_tag_index(self) -> TagIndex:
        if self._tag_index is None:
            self._tag_index = load_tag_index_from_json(self._tag_index_path)
        return self._tag_index

    def _get_main_callees(self) -> MainCalleesContext:
        if self._main_callees is None:
            self._main_callees = build_main_callees(self._routines_path)
        return self._main_callees

    def run(
        self,
        question: str,
        *,
        on_progress: Callable[[str, Any], None] | None = None,
    ) -> PipelineResult:
        """
        Run the full workflow for a question.

        Steps: extract → main_callees → grep/tags_lookup → answer → judge.

        If on_progress(stage, data) is provided, it is called after each stage
        so the caller can print or stream results immediately. Stages: extraction,
        main_callees, candidates, answer, judge.
        """
        tag_index = self._get_tag_index()

        extraction = run_extraction(question, tag_index, tags_source_path=self._tags_source_path)
        if on_progress:
            on_progress("extraction", extraction)

        main_callees_ctx = self._get_main_callees()
        if on_progress:
            on_progress("main_callees", main_callees_ctx)

        if extraction.intent.strip().upper() == "TAG_LOOKUP":
            # Evidence from tag index (and tags.md e.g. Fault Codes); no routine grep
            evidence_text = tags_lookup(
                question, extraction, tag_index, tags_md_path=self._tags_md_path
            )
            tag_block = BlockCandidate(
                block_id="T1",
                routine_name="Tag reference",
                line_hit=0,
                line_start=0,
                line_end=0,
                block_text=evidence_text,
                tag="",
            )
            candidates = [tag_block]
            selection = BlockSelectionResult(selected_block_ids=["T1"])
            selected = candidates
            grep_count = None  # no grep for TAG_LOOKUP
        else:
            candidates_raw = grep_tags(extraction, self._routines_path)
            grep_count = len(candidates_raw)
            candidates = deduplicate_blocks(candidates_raw)
            selection = BlockSelectionResult(selected_block_ids=[c.block_id for c in candidates])
            selected = candidates

        if on_progress:
            on_progress("candidates", (grep_count, candidates, selection))

        answer = run_answer_composer(
            question, selected, main_callees_ctx, tag_index=tag_index, intent=extraction.intent
        )

        judge_result: JudgeResult | None = None
        reference = find_reference(question, self._questions_path)
        if reference:
            judge_result = run_judge(question, reference, answer)
        if on_progress:
            on_progress("answer", answer)
            on_progress("judge", judge_result)

        return PipelineResult(
            question=question,
            extraction=extraction,
            main_callees=main_callees_ctx,
            candidates=candidates,
            selection=selection,
            answer=answer,
            judge_result=judge_result,
        )

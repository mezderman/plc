# PLC Question-Answering Agent

An agentic system that answers questions about PLC (Programmable Logic Controller) projects using documentation and pseudocode. Built for local-first execution with a path to containerization and cloud deployment.

---

## Design Principles

1. **Local-first, deploy-anywhere** — Designed for native local execution (like Cursor, Claude Code, OpenClaw) as well as low-latency IDE plugins—not just "runs locally" but can run embedded in the host environment. The same codebase is structured to containerize and deploy remotely when needed.

2. **Deterministic retrieval** — No embeddings, vector databases, or cosine similarity. Retrieval uses keyword grep and deterministic tools to keep behavior predictable and debuggable.

3. **Small infrastructure footprint** — No heavy dependencies beyond an LLM API. Tag index and call graph are built offline; runtime uses minimal resources.

4. **Predictability** — Retrieval is deterministic; selection is constrained to provided blocks; call-graph logic is deterministic; the composer is forced to use a small, validated evidence set.

---

## Architecture Overview

```
Question → Extraction → Call Graph → Grep / Tags Lookup → Deduplicate → Answer Composer → Judge
```

Pipeline flow:

1. **Extraction** — LLM extracts intent and resolved tags from the question.
2. **Call graph** — Builds MainRoutine execution paths from routines.md.
3. **Retrieval** — For tag lookups: `tags_lookup` (tag index + docs). For routine questions: `grep` over routines + `deduplicate_blocks`.
4. **Answer** — LLM composes an answer from selected blocks and context.
5. **Judge** — LLM scores the answer against reference `docs/questions.md`.

### Data Sources

| File | Role |
|------|------|
| `docs/tags.md` | Symbol definitions and meanings |
| `docs/routines.md` | Behavioral truth (what the PLC does) |
| `docs/questions.md` | Evaluation and reference answers |

---

## Pipeline Components

### Agents (LLM)

| Agent | Role |
|-------|------|
| **Extraction** | Converts the question into structured intent (e.g. `TAG_LOOKUP`, `ROUTINE_EXPLANATION`) and resolved tag names. Must output only tag names that exist in the tag index; if unsure, returns empty lists and populates `unknown_terms`. |
| **Answer Composer** | Produces a natural-language answer from the selected blocks, main callees context, and tag definitions. |
| **Judge** | Compares the generated answer to the reference and returns a score (0–100) and comparison table. |

### Tools (Deterministic)

| Tool | Role |
|------|------|
| **call_graph_builder** | Parses routines.md, extracts MainRoutine and its call structure, and derives possible execution paths (fault, manual, auto). |
| **grep** | Keyword search over routines for resolved tags; extracts enclosing IF/CASE blocks as candidates. |
| **tags_lookup** | For `TAG_LOOKUP` intent, pulls evidence from the tag index and docs (e.g. Fault Codes table) instead of routine code. |
| **deduplicate_blocks** | Merges blocks with the same `(routine_name, block_text)` to remove duplicates from grep output. |

### Data Flow

- **Tag index** — Prebuilt from `docs/tags.md`; maps tag names to types and descriptions.
- **Main callees** — Static per project; used to provide execution-path context to the composer.
- **Candidates** — Deduplicated code blocks passed to the composer.

### How Answers Are Generated

1. **Extraction** classifies the question (intent such as `TAG_LOOKUP`, `ROUTINE_EXPLANATION`, `TROUBLESHOOTING`, `PROCESS_FLOW`, `CONDITION_LIST`) and resolves tag names from the question.

2. **Retrieval branches on intent:**
   - **TAG_LOOKUP** — Evidence comes from the tag index and docs (e.g. fault codes table). No routine code is retrieved.
   - **Other intents** — Grep searches routines for resolved tags, extracts enclosing IF/CASE blocks, deduplicates, and passes all blocks to the composer.

3. **Answer Composer** receives only the selected blocks plus execution paths and tag context. It produces a natural-language answer tailored to the intent (e.g. numbered checklist for troubleshooting, step list for process flow).

4. **Judge** (when a reference exists in `docs/questions.md`) scores the answer and compares criterion-by-criterion.

The composer is constrained to the evidence set—it cannot invent facts or cite code outside the provided blocks.

---

## Evaluation

The Judge agent compares generated answers to reference answers in `docs/questions.md`. It outputs a criterion-by-criterion table and a 0–100 score.

### Results

Eval runs and benchmark reports are stored in the `results/` folder:

| File | Description |
|------|-------------|
| [eval_openai_20260301_092631.txt](results/eval_openai_20260301_092631.txt) | Full evaluation run for OpenAI (GPT): per-question scores, answers, and Judge criteria |
| [eval_anthropic_20260301_093815.txt](results/eval_anthropic_20260301_093815.txt) | Full evaluation run for Anthropic (Claude): per-question scores, answers, and Judge criteria |
| [openai_vs_anthropic_overview.md](results/openai_vs_anthropic_overview.md) | Benchmark comparison: accuracy, latency, behavioral differences, and practical implications |

---

## How to Run

### Prerequisites

- Python 3.10+
- OpenAI API key (required)
- Anthropic API key (optional, for `anthropic` provider)

### Setup

```bash
# Clone and enter project
cd plc_vs

# Create virtual environment and install
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env: set OPENAI_API_KEY, optionally OPENAI_MODEL and ANTHROPIC_MODEL
```

### Build Tag Index (one-time)

```bash
python -m src.ingestion.tag_index
# Writes data/tag_index.json
```

### Run Pipeline

```bash
# Interactive: enter question or question number when prompted
python test/run_pipeline.py

# Question by number (1–10 from docs/questions.md)
python test/run_pipeline.py 5

# Free-form question
python test/run_pipeline.py "What color is the stack light in manual mode?"

# Specify model provider: openai (default) or anthropic (either order)
python test/run_pipeline.py 9 openai
python test/run_pipeline.py 9 anthropic
```

**Arguments:** `[question] [provider]` or `[provider] [question]` — question is a number (1–10) or free text; provider is `openai` or `anthropic`.

### Other Scripts

```bash
# Test extraction + grep (no full pipeline)
python test/grep_test.py "What does PhotoEye_Fill do?"

# Test call graph builder
python test/test_call_graph_builder.py
```

---

## Project Layout

```
plc_vs/
├── src/
│   ├── agents/          # Extraction, answer composer, judge
│   ├── ingestion/       # Tag index from docs/tags.md
│   ├── tools/           # Grep, tags_lookup, call_graph_builder, deduplicate_blocks
│   └── pipeline.py      # Orchestrator
├── docs/                # Project data: tags, routines, questions
├── data/                # Generated: tag_index.json
├── results/             # Eval runs and benchmark reports
└── test/                # Run scripts
```

---

## Future Work and Scalability Considerations

- **Call graph predictor** — Predict the relevant MainRoutine path from the user query to optimize block selection.
- **Model selection per agent** — Configure a different model per agent (extraction, composer, judge) for cost/quality tradeoffs.
- **Planner (thinking) agent** — Generate a todo/plan to support complex, multi-step queries.
- **Cache grep results** — Cache retrieval results for performance optimization.
- **Optimize answer_composer** — Refine tone and composition structure. Intent-specific formats (checklist, step list, condition list) are in place; further optimize for conciseness, consistency, and alignment with reference answer styles.
- **Optimize extraction agent** — Develop a scalable intent extraction key (taxonomy) for future scale. As tags and question types increase, optimize for speed and cost—e.g. a fine-tuned smaller model plus algorithmic routing.
- **IDE plugin** — Expose agents as a local service for in-editor Q&A.
- **Containerization** — Package pipeline for remote deployment.
- **TypeScript port** — If native local deployment becomes strategic, port this codebase from Python to TypeScript to align with the tooling standard.

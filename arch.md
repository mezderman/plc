Goal

Answer questions in questions.md using:

tags.md for symbol definitions/meaning

routines.md for behavioral truth (what the PLC does)

overview.md optionally for generic/system context

README.md for assignment constraints (two models eval, etc.)

High-level idea

Use a multi-stage, multi-agent pipeline:

Extract concepts/tags from the question (LLM, with tags.md in context)

Retrieve candidate code blocks from routines.md (deterministic)

Select/Validate the minimal set of blocks that actually answer the question (LLM + guardrails)

Active-path context (deterministic, shallow or deep depending on intent)

Compose answer (LLM, grounded in selected blocks + citations)

Key design rule:

Tags describe “what a thing is”

Routines describe “what happens”

Final answers should be grounded primarily in routines, with tags used for naming/clarity.

Ingestion (offline step)
Inputs

tags.md

routines.md

overview.md (optional)

questions.md (for eval)

Outputs (indexes / structures)

TagIndex

tag_name -> {type, description, category}

Also store normalized_name_tokens and desc_tokens for matching (even if you mostly use LLM extraction)

RoutineIndex

routine_name -> list_of_lines

Detect routine boundaries (e.g., ### Routine: X)

Store line numbers for citations/debugging

BlockIndex (optional but helpful)

Precompute block boundaries for:

IF ... THEN ... END_IF

CASE ... OF ... END_CASE

This makes “extract enclosing block around a hit line” deterministic and fast.

CallGraph (for active path)

Parse MainRoutine for:

CALL RoutineName()

branch guards: IF Fault_Active THEN ... RETURN

Represent as edges with optional conditions:

MainRoutine -> SafetyCheck (always)

MainRoutine -> FaultHandler (when Fault_Active)

MainRoutine -> StackLightControl (when Fault_Active)

etc.

WriterIndex (optional)

symbol -> list of blocks where symbol is assigned (left side of :=)

Useful for troubleshooting/conditions questions.

Runtime pipeline (online per question)
Agent 1: Extraction Agent (LLM)

Purpose: Convert question → structured intent + resolved tags (only from tags.md).

Inputs:

user question

tags.md (or just relevant sections)

Outputs (example schema):

{
  "intent": "INDICATOR_STATE_QUERY",
  "resolved_tags": {
    "targets": ["Stack_Light_Red", "Stack_Light_Yellow", "Stack_Light_Green"],
    "conditions": ["HMI_Manual_Mode"],
    "actions": [],
    "states": []
  },
  "unknown_terms": []
}

Hard constraints:

Must output only tag names that exist in tags.md (no hallucinated symbols).

If unsure, return empty lists and populate unknown_terms.

Step 2: Deterministic Retrieval (no LLM)

Purpose: High-recall candidate collection from routines.md.

Given extracted tags:

search for each tag occurrence in routines.md

for each occurrence, extract the enclosing block (IF/CASE) or at minimum a bounded window + block expansion.

Output:

{
  "candidates": [
    {"block_id":"B12", "routine":"SafetyCheck", "start":62, "end":71, "text":"..."},
    {"block_id":"B31", "routine":"StackLightControl", "start":74, "end":82, "text":"..."},
    ...
  ]
}

This step is intentionally “dumb” and stable.

Agent 2: Block Selector / Validator Agent (LLM)

Purpose: From many candidate blocks, choose the smallest set that answers the question.

Inputs:

question

intent

resolved tags

candidate blocks (with block_id)

Outputs:

{
  "selected_block_ids": ["B31", "B05"],
  "why": {
    "B31": "Writes Stack_Light_* outputs and references HMI_Manual_Mode",
    "B05": "MainRoutine shows StackLightControl is called in execution flow"
  }
}

Guardrails (deterministic verification after LLM):

Must only select from provided block_ids

Max K blocks (e.g., 2–4)

Post-check:

At least one selected block must include a write to the target output family for indicator questions

For reset questions: at least one selected block must include Fault_Active := FALSE or Fault_Code := 0 (or equivalent)

If checks fail → fallback to deterministic scoring.

Step 4: Active Path Context Builder (deterministic)

Purpose: Add just enough execution-order context to prevent wrong reasoning.

Uses CallGraph from ingestion.

Depth selection (still one consistent step, just different depth):

D1 (1-hop): mapping questions (lights, indicators)

confirm the controlling routine is called by MainRoutine

D2 (branch path): “what happens when …” event questions

follow fault branch / manual branch

D3 (full writers): troubleshooting (“why won’t X run?”)

collect all writers of target output on active path and list blocking conditions

Output example:

{
  "active_path_routines": ["MainRoutine", "SafetyCheck", "StackLightControl"],
  "notes": ["Fault branch returns early; AutoMode skipped when Fault_Active true"]
}
Agent 3: Answer Composer (LLM)

Purpose: Produce final answer in natural language, grounded only in selected evidence.

Inputs:

question

selected blocks (raw text)

active path notes (optional)

tag descriptions for tags mentioned in final answer (optional “glossary”)

Rules:

Answer only from provided evidence

If evidence is insufficient, say what’s missing and what was searched

Multi-agent summary

Extractor Agent (LLM): question → intent + tags (using tags.md)

Retriever (code): tags → candidate code blocks (routines.md)

Selector/Validator Agent (LLM): candidate blocks → minimal evidence set (+ guardrails)

Active Path Builder (code): add scan-order / branch context as needed

Answer Agent (LLM): produce final response grounded in evidence

Why this is predictable (even with LLMs)

Retrieval is deterministic.

Selection is constrained (choose from block_ids) + verified.

Active-path logic is deterministic.

Final answer is forced to use a small, validated evidence set.

What you can keep “PoC simple”

Don’t build embeddings.

Don’t build a full AST parser.

Implement only:

routine splitter

block extractor (IF/CASE)

tag index

MainRoutine call graph parsing

LLM extraction + LLM selection with guardrails

That’s enough to answer your question set reliably.

If you want, I can turn this into a one-page checklist (“what code modules exist + inputs/outputs”) so it’s easy to implement.
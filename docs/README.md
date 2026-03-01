# Head of AI Take-Home Assignment

## Overview

PLCs.ai builds AI that understands industrial automation code. This assignment simulates a core task: building a system that can answer questions about PLC projects.

We've provided a simplified PLC project as markdown files. Your job is to build an agent that answers questions about it and compare how different LLMs perform on this task.

**Expected time: 2-3 hours**

---

## What's Included

| File | Contents |
|------|----------|
| `overview.md` | High-level description of the system (a box filling and sealing line) |
| `tags.md` | All PLC tags (variables) with types and descriptions |
| `routines.md` | Program logic in pseudocode |
| `questions.md` | 10 test questions with reference answers for evaluation |

---

## Your Task

### 1. Build a Working Agent
Create a system that can answer questions about this PLC project. The agent should be able to handle:
- Simple lookups ("What does tag X do?")
- Logic explanations ("What happens when Y occurs?")
- Troubleshooting questions ("Why won't Z start?")

Use whatever architecture you think is appropriate (RAG, context stuffing, tool use, etc.).

### 2. Compare 2 LLMs
Run the 10 questions in `questions.md` against at least 2 different LLMs. Document:
- Which models you tested
- How you scored them (define your criteria)
- Results and your recommendation
- Any interesting differences you observed

### 3. Brief Writeup (1 page max)
Cover:
- Your architecture and why you chose it
- What worked well, what didn't
- What you'd do differently if this needed to handle 100 different projects

---

## Deliverables

1. **Code** – Runnable agent (any language, include setup instructions)
2. **Evaluation results** – LLM comparison with scores and reasoning
3. **Writeup** – 1 page covering your approach and learnings

Send everything back as a zip file or GitHub repo link.

---

## Notes

- Use whatever LLMs you have access to (Claude, GPT, Gemini, open source, etc.)
- No need to over-polish. Working code with rough edges beats beautiful code that doesn't run.
- If you make assumptions or take shortcuts, just note them in your writeup.
- Questions? Email me at noam@plcs.ai 

Good luck!

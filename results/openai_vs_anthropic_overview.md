# Executive Summary

## Benchmark Comparison: GPT-5.1 vs Claude Sonnet 4.6

**Industrial PLC Logic Question Set (10 Questions)**

### Objective

This benchmark evaluates two large language models — OpenAI GPT-5.1 and Anthropic Claude Sonnet 4.6 — on their ability to reason over structured PLC logic and answer technical operational questions.

The evaluation measures:

- **Answer Quality** (Judge Score / 100)
- **Consistency** (Score Standard Deviation)
- **Response Latency**
- **Behavioral Characteristics** (reasoning style and robustness)

---

## Overall Results

| Metric | GPT-5.1 | Sonnet 4.6 |
|--------|---------|------------|
| Average Score | 97.8 / 100 | 97.3 / 100 |
| Score Std. Dev. | 2.64 | 2.00 |
| Perfect Scores (100/100) | 5 / 10 | 2 / 10 |
| Lowest Score | 92 | 93 |
| Average Latency | 9.74 sec | 19.44 sec |
| Max Latency | 15.75 sec | 32.18 sec |

---

## Key Findings

### 1. Accuracy

Both models demonstrated production-grade reliability, achieving near-perfect performance across all 10 questions.

- GPT-5.1 achieved a slightly higher average score (97.8 vs 97.3).
- GPT produced more perfect scores.
- Sonnet exhibited slightly lower variance (more stable consistency across questions).
- The performance difference in accuracy is marginal. Both models are highly capable for deterministic PLC reasoning tasks.

### 2. Latency

Latency differences were significant:

- GPT-5.1 averaged **9.74 seconds** per response
- Sonnet 4.6 averaged **19.44 seconds** per response
- GPT-5.1 was approximately **9.7 seconds faster** per query (≈2× faster overall).

For real-time industrial troubleshooting or interactive agent systems, this latency gap is operationally meaningful.

### 3. Behavioral Differences

Although scores were similar, reasoning style differed:

**GPT-5.1**
- More tightly aligned to reference logic
- Slightly more concise
- Strong structural sequencing
- Lower latency
- Fewer narrative expansions

**Sonnet 4.6**
- More verbose and explanatory
- Adds contextual safety and operational details
- Occasionally reorders sequence steps in walkthrough explanations
- Higher latency, especially on multi-step troubleshooting

### 4. Question-Type Observations

Both models performed equally well on:

- Definition-based questions
- Fault-code enumeration
- Direct logic condition queries

Minor differences appeared in:

- Multi-step event walkthroughs (sequence ordering variations)
- Troubleshooting questions (Sonnet provided broader contextual explanations)

No catastrophic reasoning failures were observed in either model.

---

## Practical Implications for Agent Architecture

Because retrieval was constrained and logic blocks were validated:

- Model differences were reduced by structured architecture.
- Deterministic retrieval and block selection play a larger role than model selection.
- **For low-latency operational agents** → GPT-5.1 is advantageous.
- **For richer explanatory output** → Sonnet provides stronger narrative context.

Both models are viable for PLC reasoning agents when paired with strong retrieval and validation pipelines.

---

## Conclusion

Both GPT-5.1 and Sonnet 4.6 demonstrate excellent capability in structured industrial control logic reasoning.

However:

- **GPT-5.1** offers significantly lower latency with slightly higher peak alignment.
- **Sonnet 4.6** offers slightly more consistent scoring and richer explanatory detail.

- For **performance-sensitive agentic systems**, GPT-5.1 provides a stronger efficiency profile.
- For **user-facing diagnostic assistants** where explanation depth matters, Sonnet is competitive.

Overall, model selection should be guided by **latency tolerance** and **desired response style** rather than raw accuracy alone.

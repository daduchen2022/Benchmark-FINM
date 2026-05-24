# Quant Interview Benchmark — v3.2 Specification

**Status**: locked. Any change to the items below requires a version bump.
**Spec date**: 2026-05-21.

## v3.2 changelog (vs v3.1)
- **No thresholding for rubric questions**. The rubric_score (1-10) is **multiplied by `RUBRIC_WEIGHT = 0.1`** and added directly to the total. Max contribution per question = 1.0 (same as a correct binary question).
- New Result field `score: float` (0.0-1.0) is the actual contribution to the total. `correct: bool | None` is now `None` for rubric questions (binary correctness no longer applies to graded-on-a-scale answers).
- `RUBRIC_PASS_THRESHOLD` removed; `RUBRIC_WEIGHT` replaces it.
- `wrong_ids` in summary renamed to `missed_ids` (any question where `score < 1.0`).
- Summary now includes a `per_category` breakdown (sums per `topic`) for each model.

## v3.1 changelog (vs v3.0) — historical
- Rubric judge path added for `answer_type: "open"` questions.
- New `rubric_score` field on Result.

## Why v3.0 (vs v2.0)

v2.0 measured **native reasoning** — all tools disabled. v3.0 turns the tools on so we can A/B against the v2.0 baseline and see how much tool use helps.

| v2.0 | v3.0 |
|---|---|
| No tools — pure native reasoning | Calculator (function calling) + web search (OpenRouter plugin) |
| Single model call per question | Multi-turn: model may iterate up to 8 tool calls before final answer |
| `tool_calls` field absent on Result | Each tool invocation logged: name, arguments, result |
| Cost ~$1–2 per run | Estimated ~$3–6 per run (web search markup + multi-turn) |

Results from v2.0 and v3.0 are not directly comparable in absolute terms. The *delta* between them is the interesting signal: how much does tool access raise each model's score, and on which questions.

> ⚠️ **Web search makes classic problems trivially solvable.** Many of our 26 questions appear on quant interview prep sites; a model that uses web search effectively will look up the canonical answer. v3.0 scores are expected to be much higher and likely cluster near the top, reducing model discrimination — that's the point of running this side-by-side with v2.0.

---

## 1. Models

Same 10 as v2.0. `supports_temperature=False` for the 3 reasoning models (claude-opus-4.7-fast, gpt-5.5, gpt-chat-latest); their sampling is still uncontrolled. All 10 models advertise `tools` + `tool_choice` support per OpenRouter's catalog (verified 2026-05-20).

---

## 2. Prompts

### Model under test — system prompt (changed from v2.0)
```
You are answering a quantitative-finance interview question. Think step by step.
You have access to a `calculator` tool for arithmetic and to live web search
(used automatically by the runtime when helpful). Use these tools whenever they
reduce error. After your reasoning, clearly state your final answer at the end.
```

### Model under test — user prompt
Bare question text from `data/questions.json`, no preamble.

### Judge — unchanged from v2.0
Same Claude Sonnet 4.6 judge prompt and the same 3-line output format (extracted / reason / YES-NO).

---

## 3. Inference / sampling parameters

| Parameter | Value | Notes |
|---|---|---|
| `temperature` | 0.0 | Honored by 7 of 10 models |
| `top_p` | 1.0 | Same |
| `max_tokens` | 8192 | Per turn |
| `seed` | not set | |
| `tools` | `[calculator]` | Function-calling protocol enabled |
| `tool_choice` | `"auto"` | Model decides when to invoke |
| `plugins` | `[{"id": "web", "max_results": 5}]` | OpenRouter web-search RAG substitute |
| Reasoning effort | Model default | |
| Sampling strategy | Single pass | No majority vote |
| Per-HTTP-call timeout (model) | 120s | One turn (one HTTP roundtrip to OpenRouter) |
| **Total answering time per question** | **120s** | Hard cap across ALL tool-loop iterations for a single (model, question). If exceeded, cell recorded as `error: TimeoutError`. |
| Per-call timeout (judge) | 60s | unchanged |
| `MAX_TOOL_ITERATIONS` | **8** | After 8 calculator calls, runtime forces the model to produce a final answer |

---

## 4. Tool permissions (v3.0 NEW)

| Tool | v3.0 | Notes |
|---|---|---|
| `calculator` (function call) | ✅ Enabled | Sandboxed Python eval over a restricted namespace (math fns + constants). Blocks `__`, `import`, `exec`, `eval`, `open`. |
| Web search | ✅ Enabled | OpenRouter's universal `plugins=[{"id": "web"}]`. Adds ~$0.004 per request. Acts as **RAG substitute** — no project-specific corpus is wired in. |
| Python code execution (arbitrary) | ❌ Disabled | Only the calculator subset is allowed |
| Function calling (general) | ✅ Protocol enabled | But the only function defined is `calculator` |
| Local RAG over a corpus | ❌ Not implemented | Would require a project-specific knowledge base; web plugin is the practical substitute |

### Calculator surface area

Supported functions/constants (whitelist):
```
abs, min, max, round, pow, sum,
sqrt, log, ln, log2, log10, exp,
sin, cos, tan,
factorial, comb, perm,
ceil, floor,
pi, e
```

Anything else (e.g., `sympy`, file IO, network) returns `Error: ...`.

---

## 5. Dataset

Target structure: **5 categories × 10 questions = 50 total**.

| Category | `topic` value | Question style | Grading |
|---|---|---|---|
| Probability | `"probability"` | Word problems, distributions, expectations | Binary |
| Brain teaser | `"brainteaser"` | Classic puzzles | Binary |
| Arithmetic | `"arithmetic"` | Mental math, estimation | Binary |
| Coding | `"coding"` | Short coding/algorithm questions | Binary |
| Finance | `"finance"` | Open-ended valuation / market questions | **Rubric (1-10)** |

Only **finance** uses `answer_type: "open"` (rubric grading). All other categories use binary grading (number / string / choice / unspecified).

**Currently incomplete**: 11 brainteaser + 15 probability = 26 questions; arithmetic, coding, finance categories are TBD. Pipeline runs regardless of completeness — once finance questions are added, the rubric path activates automatically.

Per-question schema:
```json
{
  "id": "f01",
  "topic": "finance",
  "difficulty": "medium",
  "question": "...",
  "answer": "9-10: ... / 7-8: ... / 4-6: ... / 1-3: ...",   // rubric for finance
  "answer_type": "open"                                       // triggers rubric path
}
```

Required fields: `id`, `question`, `answer`. Same hard-do-not-paraphrase rule.

---

## 6. Grading

### 6.1 Binary judge (answer_types: `number`, `string`, `choice`, or unspecified)

Single Claude Sonnet 4.6 call per (model, question). The judge sees the model's **final-turn content** as the raw response, not the intermediate tool messages. Returns 3-line response:
  - line 1: extracted answer (≤30 chars)
  - line 2: reason (≤30 chars)
  - line 3: YES or NO

`correct = (line 3 == YES)`. Stored in `judge_reasoning`. Same as v2.0 / v3.0.

### 6.2 Rubric judge (answer_type: `open`) — **v3.1 added, v3.2 changed scoring**

When `answer_type == "open"`:

- The `answer` field is **not** a single answer; it is a **rubric** (text) describing what makes a 9-10 / 7-8 / 4-6 / 1-3 answer.
- A separate Claude Sonnet 4.6 call (`judge_rubric_score`) is made instead of the binary judge.
- The rubric judge returns:
  - line 1: short summary of model's response
  - line 2: reasoning (which rubric points hit / missed)
  - line 3: a single integer 1-10
- `rubric_score = int(line 3)` (clamped to 0-10; defaults to 0 on parse failure).

**Scoring (v3.2)**: no threshold. The rubric_score is multiplied by `RUBRIC_WEIGHT = 0.1` and that value (0.0-1.0) is added directly to the model's total.

| `rubric_score` | contribution to total |
|---|---|
| 10 | 1.0 |
| 7 | 0.7 |
| 5 | 0.5 |
| 1 | 0.1 |
| 0 (parse failure / no answer) | 0.0 |

`Result.correct` is set to `None` for rubric questions (the binary correct/wrong concept doesn't apply). The leaderboard is sorted by `score_total` (sum of all `Result.score`), not by count of binary correct.

### Why 0.1 weight

Goal: every category contributes the same max points to the total. With 5 categories × 10 questions each, and binary questions worth max 1.0 each, the only way to keep finance equal to the others is to scale its 1-10 rubric down to 0.1-1.0 per question. Hence `RUBRIC_WEIGHT = 1 / max_rubric_value = 0.1`.

If you ever change the rubric scale (e.g., to 1-5), update both `RUBRIC_WEIGHT` and the rubric judge prompt's anchor descriptions.

### How to write a rubric in `data/questions.json`

The `answer` field for an open-type question should be a single string with explicit score bands. Example:

```json
{
  "id": "b12",
  "question": "Walk me through how you'd price a European call option.",
  "answer_type": "open",
  "answer": "9-10: Names Black-Scholes-Merton with all 5 inputs (S, K, T, r, σ); explains role of N(d1), N(d2); mentions risk-neutral pricing; acknowledges core assumptions (lognormal, constant σ, no dividends).\n7-8: BSM + most inputs and key intuition, may miss one assumption.\n4-6: Vague BSM mention or only some inputs; no risk-neutral or assumptions.\n1-3: Wrong framework or no quantitative content."
}
```

Bad rubrics (vague, missing bands) will make the judge inconsistent — that's on the dataset author.

### Score contribution

The rubric judge's raw 1-10 score is multiplied by `RUBRIC_WEIGHT = 0.1` (in `pipeline/clients.py`) to produce a 0.1-1.0 contribution to the model's total. **No threshold** — partial credit is preserved. If you ever change the rubric scale (e.g. to 1-5), update both `RUBRIC_WEIGHT` and the rubric judge prompt's anchor descriptions, and bump v3.x.

---

## 7. Evaluation protocol

| Setting | Value |
|---|---|
| Call granularity | 1+ model calls per question (multi-turn if tools invoked) + 1 judge call |
| Question order | ID-sorted |
| Retry policy | None in v3.0 |
| Concurrency | 8 (configurable via `--concurrency`) |
| Output format errors | If judge returns < 3 lines, parse defensively; verdict defaults to NO |

### Logged fields per (model, question) row

| Field | Description |
|---|---|
| `model` | Display name from `pipeline/models.py` |
| `question_id` | Question ID |
| `correct` | Boolean — judge's YES/NO |
| `extracted_answer` | Judge's line 1 — model's final answer |
| `expected_answer` | Dataset's reference answer |
| `raw_response` | Final-turn assistant text |
| `judge_reasoning` | Full 3-line judge response |
| `latency_s` | Wall-clock seconds for the entire model exchange (all turns) |
| `sampling_controlled` | False for the 3 reasoning models |
| `tool_calls` | **v3.0 NEW** — list of `{tool, arguments, result}` dicts. `null` if no tools used. |
| `rubric_score` | **v3.1 NEW** — integer 1-10 for `answer_type=open` questions only; `null` for all other types. |
| `score` | **v3.2 NEW** — float 0.0-1.0, the contribution to the model's total (1.0 for binary correct, 0.0 for binary wrong, `rubric_score * 0.1` for rubric). |
| `correct` | Boolean for non-rubric; **v3.2: `null` for rubric** (binary correctness doesn't apply to graded-on-scale answers). |
| `error` | Error type + message, or null |

### Output files (per run, timestamped)

Same three files as v2.0. The new `tool_calls` field appears in `details_<ts>.json`; CSV and summary are unchanged in schema.

---

## 8. How to run

```bash
LLM/bin/python run_benchmark.py
```

Estimated cost: **$3–6** per run (vs $1–2 in v2.0). Estimated wall time: **45–90 minutes** depending on how many tool roundtrips each model makes.

---

## 9. Known v3.0 limitations

1. **Web search makes classic problems trivially solvable** — many questions are on quant prep sites. Expect score ceilings clustered near 100%.
2. **Calculator is permissive** — sandbox blocks the obvious dangerous tokens but is not a hardened jail. Don't expose this to untrusted input.
3. **Tool loop iteration cap (8)** and **2-minute total answering cap** — extremely tool-heavy or slow models are cut short. A model that needs more than 2 minutes of wall time (across all tool turns) gets that cell recorded as a `TimeoutError`.
4. **No corpus RAG** — "RAG" in v3.0 = web search. If you want retrieval over project-specific documents (papers, textbook excerpts), provide a corpus and we'll wire a real retriever.
5. **Web plugin cost is non-trivial** — at ~$0.004/call × 260 calls = ~$1 extra, plus the model token cost goes up because more context is injected.
6. **All v2.0 limitations still apply** — small sample, no retry, judge as single point of failure, 3 models with uncontrolled sampling.
7. **Rubric scoring uses the same model as binary scoring (Sonnet 4.6)** — no independence. Systematic bias in Sonnet's interpretation of rubrics won't be caught by cross-checking against itself. v3.x roadmap: rubric judge should be a different model (e.g., Opus) for triangulation.
8. **`RUBRIC_WEIGHT = 0.1` is hard-coded** — tied to the 1-10 scale described in the judge prompt. Changing the rubric scale requires updating both.
9. **Current dataset has zero `answer_type: "open"` questions** — the rubric path is implemented but dormant until finance questions are added.
10. **`Result.correct` becomes a partial signal** — only meaningful for non-rubric questions. Downstream analysis should sum `Result.score` (always 0.0-1.0) and ignore `correct` for rubric rows.

---

## 10. Versioning rules

| Change type | Bump |
|---|---|
| Add or remove a model from the lineup | v3.x |
| Add or edit dataset questions | v3.x |
| Add a new tool or change tool permissions | **v4.0** |
| Change prompt, sampling params, scoring rule | **v4.0** |
| Add new logged field that doesn't alter behavior | v3.x |
| Change `RUBRIC_WEIGHT` or rubric scale | v3.x |

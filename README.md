# Quant Interview Benchmark

A small, opinionated benchmark for measuring how well frontier LLMs do on
quantitative-interview questions: **probability, brain teasers, machine
learning, corporate finance, and derivatives** (financial derivatives —
options pricing, hedging, Black-Scholes — not calculus derivatives).

Target: 5 categories × 10 questions = 50 questions. Each question contributes
at most 1.0 point. A model's final score is the sum.

For the full experimental conditions (locked spec) see [`docs/SPEC_v3.md`](docs/SPEC_v3.md).

---

## Quick start

```bash
# One-time setup
python3 -m venv LLM
LLM/bin/pip install -r requirements.txt
cp .env.example .env                  # then paste your OPENROUTER_API_KEY into .env
```

### The three commands you need

There are exactly three scripts. Use them in this order:

```bash
# 1. Standard full run — 10 models × 50 questions = 500 cells
LLM/bin/python run_benchmark.py

# 2. If the run crashed mid-flight (Python error, OOM, network storm)
LLM/bin/python resume_run.py
# Reads the partial details_*.jsonl, finds which (model, question)
# pairs are still missing, runs ONLY those. Free for already-done cells.

# 3. If the final output has `error` rows you want to retry
LLM/bin/python rerun_errors.py
# Reads the newest details_*.json, finds `error` rows, re-runs each one
# (just the judge if raw_response is preserved; otherwise model + judge).
```

All three write a NEW timestamped set of output files in `results/`; the
old files are left intact for audit. None of them ever delete data.

Iterating on one category while writing questions:

```bash
LLM/bin/python run_benchmark.py --questions data/derivatives.json
```

### Cost & time

Full run (500 cells) costs **$10–15** and takes **10–40 minutes** at
default `concurrency=8`. The breakdown:

- `gpt-5.5` ≈ $8 (priciest by far — reasoning model)
- `claude-sonnet-4.6` ≈ $2
- Other seven models combined: under $2
- Judge (`deepseek-v4-pro`): about $1

Numbers swing ±50 % depending on response length.

---

## How it works

```
                                  +-------------------------------+
data/*.json (questions) --------> | for each (model, question):   |
                                  |                               |
                                  |   1. call_model    -> raw     |  one HTTP call,
                                  |                               |  no tools
                                  |                               |
                                  |   2a. binary path             |
                                  |       judge_answer            |  -> YES / NO
                                  |   2b. open path (rubric)      |
                                  |       judge_rubric_score      |  -> 0..total_points
                                  |                               |
                                  |   3. score in [0.0, 1.0]      |
                                  +---------------+---------------+
                                                  |
                                                  v
                          results/{details,summary,scores}_<timestamp>.{json,csv}
```

**Two scoring paths**, dispatched on each question's `answer_type`:

| `answer_type` | Used by | Judge output | Contribution to total |
|---|---|---|---|
| `number` / `string` / `choice` / unset | probability, brainteaser, machine_learning, corporate_finance | 3 plain-text lines: extracted / reason / YES \| NO | `1.0` if YES else `0.0` |
| `open` | derivatives | JSON object with per-criterion scores | `raw_total / rubric.total_points` (always 0.0–1.0) |

Same judge model (`deepseek/deepseek-v4-pro`) for both paths.
No tools, no web search, no code execution — the model under test runs entirely
on its own knowledge (see [SPEC §4](docs/SPEC_v3.md)).

**Output contract for the model under test.** The system prompt instructs every
model to end its reply with a line of the form `Final Answer: <answer>` (or
`Final Answer: I don't know`). The binary judge looks for this line first and
falls back to scanning the tail of the response only if it's missing. This
eliminates the previous failure mode where the judge couldn't locate the
committed answer in a long reasoning trace.

---

## Dataset

5 files in `data/`, one per category. Pipeline loads them all and concatenates.

| Category | File | Grading | Points each |
|---|---|---|---|
| Probability | `data/probability.json` | binary 0/1 | 1.0 |
| Brain teaser | `data/brainteaser.json` | binary 0/1 | 1.0 |
| Machine learning | `data/machine_learning.json` | binary 0/1 | 1.0 |
| Corporate finance | `data/corporate_finance.json` | binary 0/1 (MCQ + numeric) | 1.0 |
| Derivatives | `data/derivatives.json` | rubric 1–10 (× 0.1) | 1.0 |

### Question schema (binary — number / string)

```json
{
  "id": "b01",
  "topic": "brainteaser",
  "question": "How many trailing zeros in 100! ?",
  "answer": "24",
  "answer_type": "number"
}
```

### Question schema (multiple choice)

Every MCQ is treated as **multi-select-possible** — the number of correct
options is not announced. `answer` is a list of all correct letters (use a
plain string when only one letter is correct).

```json
{
  "id": "cf01",
  "topic": "corporate_finance",
  "question": "Which factors apply? Select all that apply.\nA. ...\nB. ...\nC. ...\nD. ...",
  "answer": ["A", "B", "D"],
  "answer_type": "choice"
}
```

### Question schema (open / rubric)

```json
{
  "id": "d01",
  "topic": "derivatives",
  "question": "Compare option prices under different drifts ...",
  "answer_type": "open",
  "answer": {
    "total_points": 10,
    "categories": [
      {
        "name": "Asset Drift Comparison",
        "max_points": 5,
        "criteria": [
          {
            "id": "identical_prices_verdict",
            "name": "Identical Option Prices Verdict",
            "points": 2,
            "description": "Explicitly states that prices do NOT differ ...",
            "trap": "Optional: common error; if model commits this, award 0."
          }
        ]
      }
    ]
  }
}
```

Validator (runs at startup) enforces: required fields, unique IDs across files,
and rubric point totals add up consistently. See [`data/derivatives.json`](data/derivatives.json) for a worked example.

**Do not paraphrase or "clarify" a question before adding it.** If a question is
ambiguous, that ambiguity is part of the test. Only fix encoding (`Ã` → `×`)
and JSON-syntax errors.

---

## Output

Every run writes four timestamped files to `results/`:

| File | What's in it | Use it for |
|---|---|---|
| `details_<ts>.json` | One row per `(model, question)`: raw response, extracted answer, judge reasoning, latency split, token counts, cost, etc. | Auditing the judge, debugging wrong answers |
| `details_<ts>.jsonl` | Same content as the JSON, but **appended live as each cell completes**. Crash-safe source of truth. | Recovery after a crashed run |
| `summary_<ts>.json` | Per-model totals + per-category breakdown + cost / token aggregates + `missed_ids` / `error_ids` | Quick leaderboard read |
| `scores_<ts>.csv` | Model × question matrix. Cells are 0/1 (binary) or 0.0–1.0 (rubric) | Open in Excel / pandas |

### Recovery cheat sheet

Decision tree if something went wrong with the most recent run:

```
┌────────────────────────────────────────────────────────────────┐
│ Did `run_benchmark.py` finish and write a details_<ts>.json ?  │
└────────────────────────────────────────────────────────────────┘
            │                                  │
           NO (crashed mid-flight)            YES
            │                                  │
            ▼                                  ▼
   resume_run.py                  Does it have `error` rows?
   (auto-finds                            │       │
   partial jsonls,                      YES      NO
   runs missing cells,                   │       │
   writes final output)                  ▼       ▼
                                rerun_errors.py  ✅ done — read
                                (re-runs each    summary_<ts>.json
                                error cell)
```

Key idea: every script writes a NEW timestamped output set. Originals are
never touched. Worst case you end up with several `details_*` files in
`results/` and pick the newest as authoritative.

**Stale-data guard** — `resume_run.py` ignores any `details_*.jsonl`
containing rows for models not in the current `pipeline/models.py` lineup
(those are clearly from older runs with different configs). It prints
"SKIPPED stale partial(s)" when it does this.

**The judge re-run pass** — both `run_benchmark.py` and `resume_run.py`
automatically re-call the judge once for any cell that ended in
`BinaryJudgeParseError` / `RubricJudgeParseError` and has a preserved
`raw_response`. This recovers cells where the model answered fine but
the judge returned empty / unparseable output — no re-cost for the
model.

### Per-cell fields in `details_<ts>.json`

Every cell carries 20+ fields. Below is what each means — read carefully if
you plan to do downstream analysis.

| Field | Meaning |
|---|---|
| `score` | Contribution to the total. `0.0–1.0`. For binary: exactly 0 or 1; for rubric: `raw_total / total_points`. |
| `correct` | `true / false` for binary; `null` for rubric. |
| `extracted_answer` | The judge's parse of the model's committed answer. For rubric: `"rubric:N/M"`. For truncated cells: `"[truncated]"`. |
| `expected_answer` | The reference answer as-stored (string / number / list for MCQ / rubric dict for open). |
| `raw_response` | The model's full reply (may be long; reasoning models can hit several KB). |
| `judge_reasoning` | The judge's full reply (3-line plain text for binary; JSON object for rubric). |
| `sampling_controlled` | `false` for the model(s) that silently ignore our `temperature=0`. |
| `model_latency_s` | **Wall-clock seconds** for the model API call. Includes TCP/TLS, OpenRouter routing, queue, inference (with all internal reasoning), and response. |
| `judge_latency_s` | Same, but for the judge call. |
| `latency_s` | Total = `model_latency_s + judge_latency_s`. Does NOT include semaphore-wait time. |
| `model_input_tokens` | Prompt tokens consumed by the model. |
| `model_output_tokens` | **Full completion budget consumed — includes reasoning tokens.** Billing is on this number. |
| `model_reasoning_tokens` | The subset of `model_output_tokens` that was internal "thinking". `0` if the provider doesn't report it. Visible output ≈ `output_tokens − reasoning_tokens`. |
| `model_finish_reason` | `"stop"` / `"length"` / `"content_filter"` / etc. `"length"` means the model hit `max_tokens` and is counted as wrong. |
| `judge_input_tokens` / `judge_output_tokens` / `judge_reasoning_tokens` | Same semantics as the model fields, but for the judge call. |
| `model_cost_usd` | `(input × price_in + output × price_out) / 1M`. Since `output_tokens` already includes reasoning, this captures the cost of thinking automatically. |
| `judge_cost_usd` | Same, for the judge. |
| `has_final_answer_line` | `true` if the model's last ~500 chars contain a `"Final Answer:"` line — audits compliance with the output contract. |
| `rubric_score` | Raw 0–10 (or whatever the rubric's `total_points` is) for open-type. `null` for binary. |
| `rubric_breakdown` | Per-criterion `[{id, score, comment}]` for open-type. `null` for binary. |
| `error` | Exception name + message if the cell was a re-runnable error. `null` if not. |

### Per-model aggregates in `summary_<ts>.json`

`per_model[name]` rolls up `score_total`, `accuracy`, `errors`,
`missed_ids` / `error_ids`, `per_category` (sub-scores by topic), plus:
`model_cost_usd`, `judge_cost_usd`, `total_cost_usd`, total tokens
(input / output / reasoning, split by model and judge),
`avg_model_latency_s`, `avg_judge_latency_s`, `truncated_count`,
`missing_final_answer_line`. Top-level `total_cost_usd` gives the
grand total for the run.

### Automatic re-judge phase

After every `(model, question)` cell has been attempted, the runner scans
for cells whose `error` is a `BinaryJudgeParseError` or
`RubricJudgeParseError`. These are cases where the model answered fine but
the judge returned an empty / unparseable reply (e.g. a reasoning judge
burned its `max_tokens` on internal thinking before producing output). For
each such cell the judge is **re-called once**, reusing the preserved
`raw_response` — the model is NOT re-paid. The re-judge result overwrites
the original error row, both in the in-memory list and as a `# rejudge`
append in the `.jsonl` for audit.

### Post-hoc recovery: `rerun_errors.py`

If a run had errors that the automatic re-judge couldn't fix (e.g. the
model itself failed, or it's an older run with empty `raw_response` for
error rows), `python rerun_errors.py` will scan the newest
`details_*.json`, partition errors into rejudge-only vs full-rerun, and
write a NEW timestamped output that merges recovered rows with the
original ones. The original files are left intact.

### Resuming an aborted run: `resume_run.py`

If `run_benchmark.py` crashed mid-flight (e.g. a Python bug, OOM, network
storm), the partial `details_<ts>.jsonl` still contains every cell that
completed before the crash. `python resume_run.py` reads the newest
partial JSONL, figures out which `(model, question)` pairs are still
missing, runs ONLY those (no re-cost for completed cells), then writes a
fresh timestamped set of output files merging old + new. It also runs the
same automatic re-judge pass as `run_benchmark.py` to fix
`JudgeParseError` cells.

### Live terminal output

The runner streams one line per completed cell with **color-coded marks**:

| Mark | Meaning |
|---|---|
| `✓` (green) | Binary correct |
| `✗` (red) | Binary wrong |
| `5` / `3.5` (cyan, etc.) | Rubric raw score (out of 10) |
| `T` (magenta) | Model truncated at `max_tokens` |
| `E` (yellow) | Cell-level error — re-runnable |

After the run completes, the terminal also prints:
- **Leaderboard** with bar charts (green ≥75 %, cyan ≥50 %, yellow ≥25 %, red <25 %)
- **Per-category score table** — each cell colored by accuracy so you can spot strengths / weaknesses per topic
- **Cost summary** — total + per-model breakdown with bar charts
- **Token usage table** — per-model input / output / reasoning counts + average latency
- **Issues per model** — `missed_ids`, `error_ids`, truncations, and Final-Answer-line violations

---

## Repo layout

```
.
├── README.md                <- this file
├── docs/
│   ├── SPEC_v3.md           <- locked experimental spec (read this if writing it up)
│   ├── CHANGELOG.md         <- version history (v3.0 → v3.7)
│   └── archive/             <- older locked specs (v2.0 and earlier)
├── data/                    <- one JSON per category
├── pipeline/
│   ├── models.py            <- model registry (10 models, with $/Mtok pricing)
│   ├── prompts.py           <- 3 system prompts (edit prompts here, not in code)
│   ├── errors.py            <- all custom exceptions + `TRANSIENT_EXC` tuple
│   ├── clients.py           <- OpenRouter client + model call + the two judges
│   ├── dataset.py           <- load + validate questions and rubrics
│   ├── output.py            <- write details / summary / scores files
│   └── runner.py            <- Result schema, _eval_one, _rejudge_cell, plus the SHARED
│                               orchestration helpers (`run_rejudge_phase`,
│                               `row_to_result`, `make_progress`) used by all 3 scripts
├── run_benchmark.py         <- (script 1/3) standard full run
├── resume_run.py            <- (script 2/3) resume from a partial `details_<ts>.jsonl`
├── rerun_errors.py          <- (script 3/3) post-hoc recovery for `error` rows
├── requirements.txt         <- runtime deps (pinned)
└── results/                 <- benchmark outputs (gitignored)
```

Files you edit during normal iteration:

- `data/<category>.json` — add/remove questions
- `pipeline/models.py` — change the model lineup
- `pipeline/prompts.py` — tweak a prompt

The rest is set-and-forget.

---

## Design choices worth knowing

- **One key, ten models.** All API calls go through OpenRouter so you only manage one credential.
- **Single greedy decode** (`temperature=0`, `top_p=1`). One of the ten models (`gpt-5.5`) silently ignores these params — the Result records `sampling_controlled=false` for those rows so you can qualify the comparison.
- **Lineup mixes frontier + older baselines.** Seven 2026-era models plus three deliberately weaker ones (`gpt-4o`, `claude-3-haiku`, `gemini-2.5-flash`) so you can read the SOTA gap directly from the leaderboard.
- **Errors all in one place.** Custom exceptions and the `TRANSIENT_EXC` tuple live in `pipeline/errors.py`. To add a new error class that should be caught as a cell-level error, edit only that file. The runner / clients import from there.
- **One copy of the orchestration logic.** The rejudge phase, `row_to_result`, and the `progress` dict factory all live in `pipeline/runner.py` as public helpers (`run_rejudge_phase`, `row_to_result`, `make_progress`). All three entry scripts import them — no copy-paste, no drift.
- **Three-step recovery surface.** `run_benchmark.py` for the happy path; `resume_run.py` for crashes; `rerun_errors.py` for error rows. Each writes a NEW timestamped output set — old files are never overwritten. The runner also auto-rejudges any `JudgeParseError` cell whose `raw_response` is preserved (free except for one extra judge call).
- **Backward-compatible Result schema.** Every observability field (latency, tokens, cost, finish_reason, `has_final_answer_line`) has a default, so JSON rows written by older versions of the runner still round-trip cleanly through `Result(**row)`.
- **One judge, two prompts.** Binary questions get a 3-line judge prompt; rubric questions get a structured JSON-output judge prompt. Same model handles both.
- **No tools** in the current spec — the model answers on native reasoning alone. The pipeline previously supported calculator + web search (v3.0–v3.5); revert if you want those back.
- **Same prompt across all categories.** Per-category prompt engineering would confound model comparisons. This matches MMLU / GSM8K / MATH methodology.
- **Crash-safe by design.** Every completed cell is appended to a JSONL file under a lock as it finishes — a network drop mid-run does not lose data.
- **Pipeline bugs don't get silently absorbed.** Only API / timeout / judge-parse errors are captured as cell-level `error` (re-runnable). Dataset typos, SDK mismatches, etc. surface as exceptions. **Model truncation** (`finish_reason == "length"`) is counted as a wrong answer, not an error — the model failed to deliver a Final Answer in its 8192-token budget.

---

## Known limitations

These are documented in detail in [SPEC §9](docs/SPEC_v3.md). The headlines:

1. **Sample size is small.** 50 target questions is enough for ranking, not enough for tight statistical claims per category.
2. **Single judge model.** Every grading decision depends on `deepseek-v4-pro`. Audit `judge_reasoning` before publishing any leaderboard.
3. **No tools, no multi-sample.** The benchmark measures one configuration. Real deployments differ.
4. **Training-data leakage risk.** Many classic interview questions appear on prep sites, so models may be remembering rather than reasoning.

---

## Security

- `.env` holds the real API key. It's gitignored. Never commit it.
- `.env.example` is the template that **does** get committed. Keep it empty.
- If a key leaks anywhere (chat, screenshot, accidental push), rotate it at https://openrouter.ai/keys before doing anything else.

# Quant Interview Benchmark

A small, opinionated benchmark measuring how well frontier LLMs handle
quantitative-interview questions across five categories: **probability,
brain teasers, machine learning, corporate finance, and derivatives**
(financial derivatives — options pricing, hedging, Black-Scholes — not
calculus derivatives).

Target: 5 categories × 10 questions = 50 questions. Each question
contributes at most 1.0 point. A model's final score is the sum.

For the full experimental conditions (locked spec) see
[`docs/SPEC_v3.md`](docs/SPEC_v3.md).

---

## Quick start

```bash
# One-time setup
python3 -m venv LLM
LLM/bin/pip install -r requirements.txt
cp .env.example .env                  # then paste your OPENROUTER_API_KEY into .env
```

### The four commands

```bash
# 1. Standard full run — 10 models × 50 questions = 500 cells
LLM/bin/python run_benchmark.py --label run2

# 2. If the run crashed mid-flight
LLM/bin/python resume_run.py --label run2
# Reads the partial details_*.jsonl, runs only the missing cells.

# 3. If the final output has `error` rows
LLM/bin/python rerun_errors.py --label run2_fixed
# Re-runs each error cell. Cheap (only judge) when raw_response was preserved.

# 4. Re-judge an existing run with a different judge (judge swap, no model calls)
LLM/bin/python rejudge_run.py \
    --details results/details_run2.json \
    --judge anthropic/claude-sonnet-4.6 \
    --label run2_judge_sonnet
# Reuses each cell's raw_response, calls only the judge. Isolates judge effect.
```

`--label` controls the output filename suffix (defaults to a timestamp if
omitted). The scripts NEVER overwrite existing files — each writes a new
`details_<label>.{json,jsonl}`, `summary_<label>.json`, `scores_<label>.csv`
into `results/`.

**Judge selection.** Every script accepts `--judge <openrouter-id>` to
override the default judge (`deepseek/deepseek-v4-pro`). Known judges with
verified pricing are listed in `KNOWN_JUDGE_PRICING` in `pipeline/clients.py`
— add new ones there. Keep the same `--judge` across run → resume → rerun
for one experiment.

Iterating on a single category:

```bash
LLM/bin/python run_benchmark.py --questions data/derivatives.json --label deriv_only
```

### Cost & time

Full 500-cell run: roughly **$10–15**, **10–40 minutes** at the default
`concurrency=8`. The two priciest models (`gpt-5.5`, `claude-sonnet-4.6`)
account for ≈70 % of the bill. Numbers swing ±50 % with response length.

---

## How it works

```
                                  +-------------------------------+
data/*.json (questions) --------> | for each (model, question):   |
                                  |   1. call_model    -> raw     |  one HTTP call,
                                  |   2a. judge_answer  (binary)  |  no tools, no web
                                  |   2b. judge_rubric  (open)    |
                                  |   3. score in [0.0, 1.0]      |
                                  +---------------+---------------+
                                                  |
                                                  v
                          results/{details,summary,scores}_<label>.{json,csv}
```

Two scoring paths, dispatched on each question's `answer_type`:

| `answer_type` | Used by | Judge output | Contribution |
|---|---|---|---|
| `number` / `string` / `choice` / unset | probability, brainteaser, ml, corp_finance | 3 plain-text lines: extracted / reason / YES \| NO | `1.0` if YES else `0.0` |
| `open` | derivatives | JSON object with per-criterion scores | `raw_total / rubric.total_points` (0.0–1.0) |

Same judge model (`deepseek/deepseek-v4-pro`) for both paths.

**Output contract for the model under test.** The system prompt requires
every model to end its reply with a line of the form `Final Answer: <answer>`
(or `Final Answer: I don't know`). The binary judge looks for this line first
and falls back to scanning the tail only if it's missing.

---

## Dataset

Five files in `data/`, one per category. Pipeline loads them all and
concatenates.

| Category | File | Grading |
|---|---|---|
| Probability | `data/probability.json` | binary 0/1 |
| Brain teaser | `data/brainteaser.json` | binary 0/1 |
| Machine learning | `data/machine_learning.json` | binary 0/1 |
| Corporate finance | `data/corporate_finance.json` | binary 0/1 (MCQ + numeric) |
| Derivatives | `data/derivatives.json` | rubric 1–10 (× 0.1) |

### Schemas

Binary (number / string):
```json
{ "id": "b01", "topic": "brainteaser", "question": "How many trailing zeros in 100! ?",
  "answer": "24", "answer_type": "number" }
```

Multiple-choice (always treated as multi-select-possible):
```json
{ "id": "cf01", "topic": "corporate_finance",
  "question": "Which factors apply?\nA. ...\nB. ...\nC. ...\nD. ...",
  "answer": ["A", "B", "D"], "answer_type": "choice" }
```

Open / rubric (only used by `derivatives`):
```json
{ "id": "d01", "topic": "derivatives", "question": "...",
  "answer_type": "open",
  "answer": {
    "total_points": 10,
    "categories": [{
      "name": "Asset Drift Comparison", "max_points": 5,
      "criteria": [{
        "id": "identical_prices_verdict", "name": "...",
        "points": 2, "description": "...",
        "trap": "Optional: common error; if model commits this, award 0."
      }]
    }]
  }
}
```

Validator (runs at startup) enforces: required fields, unique IDs across
files, valid `answer_type` values, and rubric point-totals adding up.

**Do not paraphrase or "clarify" a question before adding it.** If a
question is ambiguous, that ambiguity is part of the test. Only fix
encoding (`Ã` → `×`) and JSON-syntax errors.

---

## Output

Every run writes four files to `results/`, suffixed by `--label` (or
timestamp). Pick whichever fits your task:

| File | Contents | Use for |
|---|---|---|
| `details_<label>.json` | One row per `(model, question)` with raw response, judge text, latency / token / cost breakdown | Auditing the judge, debugging |
| `details_<label>.jsonl` | Same content, appended live as each cell completes | Crash recovery (read by `resume_run.py`) |
| `summary_<label>.json` | Per-model totals + per-category breakdown + cost / token aggregates | Quick leaderboard read |
| `scores_<label>.csv` | Model × question matrix (0/1 binary, 0.0–1.0 rubric) | Excel / pandas |

Field-level reference (24 fields per cell, schema invariants, etc.) lives in
[SPEC §7](docs/SPEC_v3.md#7-evaluation-protocol).

After the run finishes, the terminal also prints a color-coded
**leaderboard** (with score bars), a **per-category** table, a **cost
summary**, **token usage**, and **issues per model**.

---

## Repo layout

```
.
├── README.md                <- this file
├── docs/
│   ├── SPEC_v3.md           <- locked spec; field reference, design rationale
│   ├── CHANGELOG.md         <- version history (v3.0 → v3.10)
│   └── archive/             <- older locked specs
├── data/                    <- one JSON per category
├── pipeline/
│   ├── models.py            <- model registry (10 models, with $/Mtok pricing)
│   ├── prompts.py           <- 3 system prompts
│   ├── errors.py            <- all custom exceptions + TRANSIENT_EXC tuple
│   ├── clients.py           <- OpenRouter client + model call + the two judges
│   ├── dataset.py           <- load + validate questions and rubrics
│   ├── output.py            <- write details / summary / scores files
│   └── runner.py            <- Result schema, per-cell evaluation, shared
│                               orchestration helpers (rejudge, row_to_result)
├── run_benchmark.py         <- (script 1/4) standard full run
├── resume_run.py            <- (script 2/4) resume from a partial jsonl
├── rerun_errors.py          <- (script 3/4) re-run `error` rows
├── rejudge_run.py           <- (script 4/4) re-judge an existing run with a different judge
├── requirements.txt         <- runtime deps (pinned)
└── results/                 <- benchmark outputs (gitignored)
```

Files you typically edit:

- `data/<category>.json` — add / remove questions
- `pipeline/models.py` — change the model lineup
- `pipeline/prompts.py` — tweak a prompt

The rest is set-and-forget.

---

## Design choices worth knowing

- **One key, ten models.** All API calls go through OpenRouter so you manage one credential.
- **Single greedy decode** (`temperature=0`, `top_p=1`). One of the ten models (`gpt-5.5`) silently ignores these — Result records `sampling_controlled=false` so you can qualify the comparison.
- **Lineup mixes frontier + older baselines.** Seven 2026-era models plus three deliberately weaker ones (`gpt-4o`, `claude-3-haiku`, `gemini-2.5-flash`) so you can read the SOTA gap directly.
- **No tools.** The model answers on native reasoning alone. To re-enable calculator / web search, check the v3.0–v3.5 entries in [`CHANGELOG.md`](docs/CHANGELOG.md).
- **Same prompt across all categories.** Per-category prompt engineering would confound model comparisons (matches MMLU / GSM8K / MATH methodology).
- **Crash-safe by design.** Every completed cell is appended to a JSONL under a lock as it finishes — a network drop mid-run loses zero data.
- **Three-step recovery, never destructive.** `run_benchmark.py` → `resume_run.py` (crashes) → `rerun_errors.py` (error rows). Each writes a NEW `--label`ed output set. The runner also auto-rejudges any `JudgeParseError` whose `raw_response` was preserved (cheap — no model re-call).
- **Errors all in one place.** Custom exceptions and `TRANSIENT_EXC` live in `pipeline/errors.py`. To catch a new error class as a cell-level error, edit only that file.
- **Pipeline bugs don't get silently absorbed.** Only API / timeout / judge-parse errors become cell-level `error` (re-runnable). Dataset typos, SDK mismatches, etc. surface as exceptions. **Model truncation** (`finish_reason == "length"`) is counted as a wrong answer, not an error.
- **Backward-compatible Result schema.** Every observability field has a default — older-version JSONL rows still round-trip cleanly through `Result(**row)`.
- **Numeric pre-check fast-path.** Before calling the binary judge, the pipeline tries to parse both expected and the model's committed answer as clean numerics (decimal / percent / fraction / `$199,900.46`-style currency). If they agree within ~0.01% relative tolerance, the cell auto-passes deterministically — no judge call. Skips ~20% of binary cells, eliminates judge-model variance for the easy numeric path. Disagreements still fall through to the judge.
- **Tolerant judge output parser.** The rubric judge has been observed to emit JSON with trailing commas (gemini), whitespace-padded keys (`" scores"`, deepseek), and chain-of-thought prose followed by raw JSON (sonnet). The parser handles all three before raising `RubricJudgeParseError`.

---

## Known limitations

See [SPEC §9](docs/SPEC_v3.md) for the full list. The headlines:

1. **Sample size is small** — 50 questions is enough for ranking, not for tight per-category claims.
2. **Single judge model.** Every grade depends on `deepseek-v4-pro`. Audit `judge_reasoning` before publishing.
3. **No tools, no multi-sample.** The benchmark measures one configuration.
4. **Training-data leakage risk.** Many classic interview questions appear on prep sites.

---

## Security

- `.env` holds the real API key — gitignored, never commit it.
- `.env.example` is the template that **does** get committed. Keep it empty.
- If a key leaks anywhere (chat, screenshot, accidental push), rotate at https://openrouter.ai/keys before doing anything else.

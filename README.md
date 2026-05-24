# Quant Interview Benchmark

A scored benchmark of LLM performance on **quantitative-finance interview questions**. Each question contributes max 1.0 point — binary questions are 0 or 1, rubric (finance) questions are `rubric_score × 0.1` (0.0 to 1.0). Target dataset: 50 questions across 5 categories (currently 26 collected; rest TBD).

Currently at **v3.2**. See [docs/SPEC_v3.md](docs/SPEC_v3.md) for the locked experimental conditions.

---

## What this measures

A model is given a quant interview question and asked to answer step-by-step. We then:

1. **Model answers** (a paragraph of reasoning + a final answer)
2. **An LLM judge** (Claude Sonnet 4.6) sees `(question, expected, full raw response)` and returns: extracted final answer, one-line reason, and a YES/NO verdict
3. **Score** = number of YES verdicts out of N

There is no code-based grader. All grading goes through the same LLM judge — no separate paths for numbers vs strings vs sentences. This eliminates the v1.x class of bugs where `√5`, fractions with annotations, or sentence answers couldn't be parsed by regex rules.

The benchmark is part of a 4-stage project:
1. Define benchmark (topics / distribution / difficulty)
2. Build dataset ([question, answer] pairs, human-verified) — **upstream of this repo**
3. **Evaluation pipeline ← this repo**
4. Analyze results, detect leakage / poor discrimination, iterate

---

## Pipeline (what actually happens when you run it)

```
data/questions.json (26 quant questions)
        │
        ▼
   for each (model, question):
        │
        ├─► call_model()  ──────────► OpenRouter ─► 10 models (Claude / GPT / Gemini / ...)
        │                                                │
        │                                                ▼
        │                                         raw_response  (paragraph)
        │                                                │
        │                                                ▼
        ├─► (if answer_type != "open")
        │   judge_answer(q, expected, raw) ─► Claude Sonnet 4.6
        │                                          │
        │                                          ▼
        │                              3-line: extracted / reason / YES|NO
        │                                          │
        │                                          ▼
        │                              correct = (verdict == YES)
        │                              score   = 1.0 if correct else 0.0
        │
        └─► (if answer_type == "open")
            judge_rubric_score(q, rubric, raw) ─► Claude Sonnet 4.6
                                                       │
                                                       ▼
                                       3-line: summary / reasoning / 1-10
                                                       │
                                                       ▼
                                          rubric_score = N           (1-10)
                                          score        = N × 0.1     (0.1-1.0)
                                          correct      = None        (rubric: no binary)
        │
        ▼
   results/{details,summary,scores}_<timestamp>.{json,csv}
```

Per run: 260 model calls + 260 judge calls = **~520 OpenRouter requests**. Cost: ~$1–2.

---

## Repo file map

Files marked **★** are the ones you'll edit during normal iteration. Everything else is set-and-forget infrastructure.

### Top-level

#### [`README.md`](README.md)
This file. Project overview, file map, output explanation, key v3.2 decisions, how to run, known limitations.

#### **★** [`run_benchmark.py`](run_benchmark.py)
CLI entry point — the **only script you'll ever run directly**. Three jobs:
1. Loads `.env` into the environment via `python-dotenv`
2. Parses CLI flags (`--questions` / `--out` / `--concurrency`)
3. Calls `pipeline.runner.run_benchmark()` and prints a leaderboard

#### [`requirements.txt`](requirements.txt)
Python dependencies, **versions pinned** (`openai==1.59.9`, `python-dotenv==1.0.1`). Pinning is intentional for reproducibility — a benchmark re-run six months from now shouldn't behave differently because the SDK changed under us. Bump versions deliberately and record it as a v3.x bump.

#### [`.env.example`](.env.example)
Environment-variable **template**. Lists the required keys (`OPENROUTER_API_KEY`, optional `OPENROUTER_REFERER`, `OPENROUTER_TITLE`) with **empty values**. Committed to git. **Never put real secrets here.**

#### `.env` (gitignored) ⚠️
Where your **real** `OPENROUTER_API_KEY` lives. Excluded by `.gitignore`. If you ever paste this key publicly (chat, screenshot, accidental commit), rotate it at https://openrouter.ai/keys.

#### [`.gitignore`](.gitignore)
Excludes from version control: `.env`, all common venv directory names (including `LLM/`), `__pycache__/`, `results/` (every run regenerates), IDE configs, `.DS_Store`, `*.key`.

---

### `data/` — dataset

#### Dataset structure: 5 categories × 10 questions = 50 total

| Category | `topic` value | Style | Grading | Max points per question |
|---|---|---|---|---|
| Probability | `"probability"` | Word problems, distributions, expectations | Binary 0/1 | 1.0 |
| Brain teaser | `"brainteaser"` | Classic puzzles, lateral thinking | Binary 0/1 | 1.0 |
| Arithmetic | `"arithmetic"` | Mental math, estimation | Binary 0/1 | 1.0 |
| Coding | `"coding"` | Short algorithm / code questions | Binary 0/1 | 1.0 |
| Finance | `"finance"` | Open-ended valuation / market questions | **Rubric 1-10 × 0.1** | 1.0 |

Each category contributes **max 10 points** to a model's total (10 questions × 1.0). Total max = **50 points** across all 5 categories.

**Why the rubric weight is 0.1**: finance answers are graded on a 1-10 scale (rubric judge). Multiplying by 0.1 makes the max contribution per finance question equal to 1.0, keeping every category on equal footing in the total.

**Current state of dataset** (`data/questions.json`):

| Category | Status |
|---|---|
| Probability | 15 questions ✓ (need to trim to 10) |
| Brain teaser | 11 questions ✓ (need to trim to 10) |
| Arithmetic | **0 questions** — TBD |
| Coding | **0 questions** — TBD |
| Finance | **0 questions** — TBD (rubric path is dormant until added) |

Pipeline runs regardless of completeness. As soon as `answer_type: "open"` questions are added under `topic: "finance"`, the rubric judge activates automatically.

#### **★** [`data/questions.json`](data/questions.json)
The questions file. **Swap this file when you have more interview questions** — nothing else in the pipeline needs to change.

Schema per entry:
```json
{
  "id": "b01",                  // unique; becomes column name in scores CSV
  "question": "...",            // sent verbatim to the model — DO NOT paraphrase or add conditions
  "answer": "56",               // ground truth — sent verbatim to the judge
                                // ↳ if answer_type=="open", this field is a RUBRIC string instead
  "topic": "brainteaser",       // optional metadata
  "difficulty": "easy",         // optional metadata
  "answer_type": "number"       // "number" | "string" | "choice" | "open"
                                // ↳ "open" routes through the rubric judge (v3.1)
                                // ↳ other values share the binary judge path
}
```

**Required**: `id`, `question`, `answer`. Everything else is optional, but `answer_type: "open"` is what triggers the rubric path — for those questions the `answer` field must contain a real rubric with 1-3 / 4-6 / 7-8 / 9-10 score bands (see [SPEC § 6.2](docs/SPEC_v3.md)).

**Important rule**: never paraphrase a question to "clarify" it or add conditions. If a question is ambiguous, that ambiguity is part of the test. Fix only encoding artifacts (`Ã` → `×`) and JSON-syntax errors. See [docs/SPEC_v3.md § 5](docs/SPEC_v3.md).

`run_benchmark.py` validates this file at startup: missing required fields and duplicate IDs cause an immediate exit before any API calls are made.

---

### `pipeline/` — core code

#### [`pipeline/__init__.py`](pipeline/__init__.py)
Empty file. Its presence tells Python that `pipeline/` is a package, so `from pipeline.runner import run_benchmark` works. **Should stay empty.**

#### **★** [`pipeline/models.py`](pipeline/models.py)
The model registry. A `MODELS` list of `ModelConfig` entries, each with three fields:
- `name` — display label (appears in CSV/JSON output)
- `model_id` — OpenRouter's identifier (verified against `/api/v1/models`)
- `supports_temperature` — `False` for the 3 reasoning models that ignore sampling params

**Edit this file to add, remove, or swap models.** No other code changes needed.

#### [`pipeline/clients.py`](pipeline/clients.py)
All OpenRouter network code. Two public async functions:

- `call_model(cfg, prompt) → str` — sends the question to a model under test, returns its raw response
- `judge_answer(question, expected, raw_response) → (bool, str, str)` — binary judge. Returns `(is_correct, extracted_answer, full 3-line judge text)`. Used when `answer_type` is `number` / `string` / `choice` or unspecified.
- `judge_rubric_score(question, rubric, raw_response) → (int, str)` — **v3.1** rubric judge. Returns `(score 1-10, full 3-line judge text)`. Used when `answer_type == "open"`.

Constants worth knowing:
- `MODEL_SYSTEM_PROMPT` — instructions sent to every model under test
- `JUDGE_SYSTEM_PROMPT` — binary judge prompt (output: extracted / reason / YES/NO)
- `RUBRIC_JUDGE_SYSTEM_PROMPT` — rubric judge prompt (output: summary / reasoning / 1-10)
- `RUBRIC_WEIGHT = 0.1` — rubric contribution = rubric_score × this. Tied to the 1-10 scale.
- `JUDGE_MODEL = "anthropic/claude-sonnet-4.6"` — change one line to swap judges

A lazy-singleton `AsyncOpenAI` client is used so we open one HTTP connection pool for all ~520 calls per run. Hard timeouts: 180s for the model under test, 60s for the judge.

#### [`pipeline/runner.py`](pipeline/runner.py)
Orchestration. Defines:
- `Result` dataclass — the fields logged per `(model, question)` call (see below)
- `_validate(questions)` — startup sanity check on `data/questions.json`
- `_eval_one(cfg, q, sem, progress)` — the per-pair flow: `call_model → judge_answer`, wrapped in try/except so any single failure becomes an `error` row instead of crashing the whole run. Prints progress as `[N/total] model qid mark latency`.
- `run_benchmark(...)` — fans out all `model × question` tasks with `asyncio.Semaphore(concurrency=8)` for rate-limiting
- `_write_outputs(...)` — produces the three output files

---

### `docs/` — specification

#### [`docs/SPEC_v3.md`](docs/SPEC_v3.md)
The **locked v3.2 specification** — 10 sections covering exactly which models, prompts, sampling params, tool permissions, dataset format, judge model, scoring rules (binary + rubric), evaluation protocol, known limitations, and versioning rules apply. This is what you'd quote in a methods section of a writeup, and what future you needs to read before changing anything that would break comparability.

---

### Runtime artifacts (gitignored)

#### `LLM/` — Python virtual environment
Created with `python3 -m venv LLM`. ~200 MB after `pip install -r requirements.txt`. Tied to this machine's Python — recreate on another machine, don't commit. The `★` files run with `LLM/bin/python` (or after `source LLM/bin/activate`).

#### `results/` — benchmark outputs
Three timestamped files per run. Accumulates over time so you can compare runs (before/after a prompt change, etc.). Prune manually when it gets cluttered.

---

## Output files (what the 3 results files actually contain)

Each run of `python run_benchmark.py` produces three files in `results/`, all sharing a timestamp `YYYYMMDD-HHMMSS`. They contain **the same evaluation results** in three formats optimized for different uses.

### `details_<ts>.json` — the raw record (debugging / auditing)

A JSON array, one entry per `(model, question)` pair (= num_models × num_questions). **This is where the truth lives**; the other two files are derived from it.

Each entry — binary (non-rubric) example:

```json
{
  "model": "claude-opus-4.7-fast",
  "question_id": "b01",
  "score": 1.0,                       // contribution to total (0.0 or 1.0 for binary)
  "correct": true,                    // binary verdict
  "extracted_answer": "56",           // judge's line-1
  "expected_answer": "56",
  "raw_response": "...",              // model's final-turn text
  "judge_reasoning": "...",           // judge's full 3-line response
  "latency_s": 2.55,
  "sampling_controlled": false,       // did our temperature=0 actually apply?
  "tool_calls": null,                 // or list of {tool, arguments, result}
  "rubric_score": null,               // null for binary
  "error": null
}
```

Rubric (open-type) example:

```json
{
  "model": "claude-sonnet-4.6",
  "question_id": "f03",
  "score": 0.8,                       // = rubric_score × 0.1
  "correct": null,                    // not applicable to rubric
  "extracted_answer": "rubric:8/10",
  "expected_answer": "9-10: ... 7-8: ...",   // the rubric text
  "rubric_score": 8,                  // raw 1-10
  "judge_reasoning": "summary line\nreasoning line\n8",
  ...
}
```

Use this file when you want to **audit the judge** (compare `raw_response` to `judge_reasoning`), **debug missed points** (model, judge, or rubric?), or measure latency. Typical size: 100–500 KB depending on reasoning model verbosity.

### `summary_<ts>.json` — per-model totals (quick read)

One block per model with totals and per-category breakdown:

```json
{
  "timestamp": "20260520-152016",
  "num_questions": 26,
  "num_models": 10,
  "rubric_weight": 0.1,
  "max_possible_score": 26.0,
  "per_model": {
    "claude-sonnet-4.6": {
      "score_total": 23.4,            // sum of all `score` fields
      "total": 26,                    // questions answered
      "errors": 0,
      "missed_ids": ["p03", "f02"],   // score < 1.0 and no error
      "error_ids": [],
      "per_category": {
        "probability":  {"score": 9.0,  "total": 10, "accuracy": 0.9},
        "brainteaser":  {"score": 10.0, "total": 11, "accuracy": 0.91},
        "finance":      {"score": 4.4,  "total":  5, "accuracy": 0.88}
      },
      "sampling_controlled": true,
      "accuracy": 0.9
    },
    ...
  },
  "details_file": "details_20260520-152016.json"
}
```

`score_total` is the sum of contributions; `accuracy` is `score_total / total`. `missed_ids` lists questions where the model didn't get max points (includes partial rubric scores). `per_category` lets you see if a model is strong at, say, probability but weak at finance.

### `scores_<ts>.csv` — the model × question matrix (analysis)

A spreadsheet. Rows = models (sorted by `score_total` desc). Cell values: integer `0` or `1` for binary questions, decimal `0.0`–`1.0` for rubric questions.

```
model,b01,b02,...,p01,...,f01,...,score,accuracy,sampling_controlled
claude-sonnet-4.6,1,1,...,1,...,0.8,...,23.40,0.900,yes
gpt-5.5,1,1,...,1,...,0.7,...,22.10,0.850,no
...
```

Open in Excel, Numbers, or pandas. The matrix view makes it obvious which questions discriminate (column has mixed values) versus which are trivially easy (all 1) or impossibly hard (all 0).

### Why timestamped and not overwriting

Each run is an experiment. You'll want to compare — same dataset, different prompt; same prompt, different models; same setup, different days. Cleanup is your job:

```bash
ls -t results/details_*.json | tail -n +4 | xargs rm   # keep the 3 most recent runs
rm results/*.{json,csv}                                # nuke everything
```

---

## Key v3.2 decisions

**Models**: 10, all routed through **OpenRouter** (one API key reaches everyone). Versions are pinned, no `~latest` aliases — runs months apart should be comparable.

**Routing — why OpenRouter, not direct APIs**:
- One key vs 8 separate provider accounts
- New models on OpenRouter the day they launch
- Cost: ~5% markup, irrelevant at our volume
- Trade-off: can't use provider-exclusive features (Claude extended-thinking mode, OpenAI logprobs, etc.)

**Three models silently ignore our sampling settings** — surfaced in results via `sampling_controlled=false`:
- `anthropic/claude-opus-4.7-fast`
- `openai/gpt-5.5`
- `openai/gpt-chat-latest`

These reasoning models don't expose `temperature` / `top_p` controls; OpenRouter drops those params. The other 7 honor them.

**Prompt**: Zero-shot. Brief system prompt asks for chain-of-thought reasoning + a clearly-stated final answer. No "Final answer: X" format requirement (judge sees the full reply). No few-shot examples (avoids contaminating answer style).

**Sampling**: `temperature=0`, `top_p=1.0`, `max_tokens=8192`. Greedy decoding for reproducibility.

**Tools ENABLED in v3.0+**: calculator (sandboxed function call) + web search (OpenRouter `plugins=[{"id":"web"}]`, acts as RAG substitute). v2.0 was the "no tools" baseline; v3.0+ uses tools so we can measure tool-augmented performance.

**Grading — two paths dispatched on `answer_type`**:

1. **Binary path (default)** — for `answer_type` in `{number, string, choice}` or unspecified. Used by probability / brainteaser / arithmetic / coding.
   - One Claude Sonnet 4.6 call sees `(question, expected, full raw)` → 3 lines: extracted / reason / YES|NO.
   - `correct` = (verdict == YES). **Contribution to total = 1.0 if correct, else 0.0.**
   - Tolerates: numerical closeness (`0.667` ≈ `0.6667` ≈ `2/3`), math symbols (`√5` ≈ `2.236`), latex, semantic equivalence (`down` ≈ `decreases`), partial-match on multi-part questions.

2. **Rubric path (v3.1, scoring updated in v3.2)** — for `answer_type: "open"`. Used by finance.
   - The `answer` field is interpreted as a **rubric** (text with 1-3 / 4-6 / 7-8 / 9-10 score bands).
   - One Claude Sonnet 4.6 call (separate prompt) scores model's reply **1-10** against the rubric.
   - **Contribution to total = `rubric_score × 0.1`** (so 10/10 → 1.0, 7/10 → 0.7, etc.). No threshold — partial credit is preserved.
   - `Result.correct` is set to `None` (binary correctness doesn't apply); `Result.rubric_score` holds the raw 1-10.

**Total score for a model** = sum of `Result.score` over all questions. Max possible = number of questions (50 in the target dataset). The leaderboard is sorted by this float total. `judge_reasoning` stores the full 3-line judge text in both paths so any verdict is auditable.

**Not in v3.2** (deferred):
- Retry on transient errors
- Token / cost / reasoning-token logging
- Majority vote / multi-sample
- LLM-as-judge for grading (LLM is used only for extraction; correct/wrong is pure code)
- Mandatory human review pass before publishing a leaderboard

---

## How to run

```bash
# One-time setup
python3 -m venv LLM                          # create ./LLM/ venv
LLM/bin/pip install -r requirements.txt
cp .env.example .env                         # then fill OPENROUTER_API_KEY in .env

# Run
source LLM/bin/activate                      # or use LLM/bin/python directly
python run_benchmark.py                      # ~30s–2min, $0.30–$0.80
deactivate

# Inspect
cat results/scores_*.csv                     # quick view
python -m json.tool results/summary_*.json   # per-model totals
```

CLI flags:
```
--questions PATH    use a different question file (default: data/questions.json)
--out DIR           write outputs to a different directory (default: results/)
--concurrency N     max in-flight API calls (default: 8)
```

---

## Known v3.2 limitations

1. **Sample size 26 currently / 50 target** — still small; statistical power weak. Expand as more questions get curated.
2. **No retry on transient errors** — a single API failure leaves that cell as `error`.
3. **Training-data contamination risk** — classic interview problems may be memorized.
4. **3 of 10 models can't have controlled sampling** — qualified via `sampling_controlled` flag.
5. **Judge is itself an LLM** — could occasionally misextract; manual audit of edge cases is required before publishing.
6. **No tool use** — doesn't reflect realistic LLM usage today; deferred.
7. **Judge accuracy is a single point of failure** — every grading decision depends on Sonnet. Audit `judge_reasoning` before publishing.

See [docs/SPEC_v3.md § 9](docs/SPEC_v3.md) for the full list.

---

## Security note

**Never put a real API key in `.env.example`** — it's committed to git. Real secrets go in `.env`, which is gitignored. If you accidentally commit (or paste) a real key anywhere public, rotate it immediately at https://openrouter.ai/keys.

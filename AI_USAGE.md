# AI Usage Statement

This document discloses every AI tool used in this submission, exactly what
each tool produced, where it helped, and how we verified its output. Read it
as a disclosure of where coding-assistant output appears in the repo — not as
an accounting of who designed the benchmark. **The design is unambiguously
ours**; the AI was used to implement those designs and to draft first-pass
code and prose, both of which we reviewed, rejected, and rewrote throughout.

## 1. Tools used (full disclosure)

- **Claude Code (Anthropic, Opus-class model)** — interactive coding agent
  used for code implementation, debugging, and data wrangling. Used
  interactively across many sessions: we prompted, it produced, we
  reviewed before any commit.
- **OpenRouter** — the routing layer the benchmark itself calls. This is the
  *object of study*, not an authoring tool, listed for completeness.
- **Nothing else.** No GitHub Copilot, no Cursor, no standalone ChatGPT
  sessions, no Gemini / Claude.ai browser sessions used to produce content
  in this submission.

## 2. What we decided and drove (the substantive work)

Everything in this section was specified, debated, and decided by us. The AI
was used to implement, not to author the substance.

### Benchmark design — ours

- The 5 categories (probability / brainteaser / machine learning / corporate
  finance / derivatives), based on what quant-trading interviews actually
  test.
- The composition: 50 closed-form / multi-select questions + 10 open-ended
  derivatives questions graded by rubric.
- Question selection criteria — closed-form answers so a judge can verify,
  difficulty range that discriminates frontier from baseline, mix of
  symbolic (`n!`, `1/(k+1)`, `1 − n/2^(n-1)`) and numerical (`2961/32`,
  `5/28`) answers, at least one item (`p06`) adjacent to a memorized
  classic to detect pattern-matching rather than reasoning.
- The 50 questions themselves — we curated and verified every one. We
  rejected questions that were ambiguous, too memorizable, or not
  discriminative.
- The **no-tools experimental condition** — our decision to measure native
  reasoning rather than tool use.
- The **rubric schema for derivatives** (`total_points` / `categories` /
  `criteria` / `trap` field for catching common LLM failure modes) — we used AI in a limited assistive way to help organize possible rubric structures for open-ended responses, such as separating key conceptual points and common failure modes into criteria. However, the final rubrics, scoring logic, criteria weights, and trap conditions were ultimately designed and verified by us based on our own understanding of derivatives pricing
- The **MCQ semantics** — "every multiple-choice question is potentially
  multi-select; the number of correct options is not announced" — our
  decision, with corresponding judge-prompt rule.
- The **`Final Answer:` output contract** — our solution after observing
  silent mis-grading in early runs, where judges couldn't locate the
  committed answer in long reasoning traces.

### Model lineup — ours

- We chose the 10 models, debated frontier vs baseline composition, and made
  specific swaps as we iterated: added `seed-2.0-lite`, removed
  `kimi-k2.6` / `minimax-m2.7` / `gpt-chat-latest`, swapped `gpt-4` to
  `gpt-4o` after observing the original GPT-4 cost was ~30× per token vs the
  rest.
- The decision to keep three deliberately weaker baselines (`gpt-4o`,
  `claude-3-haiku`, `gemini-2.5-flash`) — ours, so the SOTA gap is legible
  on the same questions.

### Pipeline architecture — ours

- The module split (`clients` / `dataset` / `output` / `runner` / `errors`
  / `prompts`) was specified by us when the original single-file runner got
  too long; the AI's first attempt was monolithic and we pushed back twice.
- The **pluggable judge design** (`KNOWN_JUDGE_PRICING` dict +
  `clients.set_judge()` + `--judge` CLI flag) — our spec, motivated by the
  cross-judge experiment we wanted to run.
- The **three-step recovery surface** (`run_benchmark` → `resume_run` →
  `rerun_errors`, later `rejudge_run`) and the principle that none of them
  ever overwrite — our design.
- **Deduplicating orchestration** into shared helpers (`run_rejudge_phase`,
  `row_to_result`, `make_progress`) — we noticed the copy-pasted blocks
  across the three entry scripts and ordered the cleanup.
- The **`Result` schema choices** — every observability field carries a
  default so older-version JSONL rows still round-trip; this was our call
  after the AI-introduced lack-of-defaults broke the resume path.
- The **errors module** (`pipeline/errors.py` + `TRANSIENT_EXC` tuple as
  single source of truth) — we ordered the consolidation; the AI's first
  layout had exception classes scattered across `clients.py`.

### Judge selection and evaluation methodology — ours

- The decision to do a **cross-judge reliability study** — re-grading the
  same model outputs with multiple judges — was ours. The AI did not
  propose this.
- The choice of 5 judges to compare (`deepseek-v4-pro`, `gemini-3.1-flash-lite`,
  `claude-sonnet-4.6`, `grok-4.3`, `qwen3.6-flash`) — ours, with explicit
  thinking about same-vendor bias.
- The **per-category judge-disagreement audits** (probability / brainteaser
  / corporate finance / machine learning) — we asked for them specifically:
  *"summarize where the 3 judges disagree on each category, with the model
  outputs and each judge's reasoning, so we can see WHY they differ."*
- **We discovered the verdict-parser bug.** While reading the disagreement
  audits we noticed that the recorded extracted answer was `"Line 1: n!"`
  and the verdict line was `"Line 3: YES"`, yet the cell was scored 0. We
  hypothesised (correctly) that `last_line.startswith("YES")` was failing
  whenever the judge prefixed the verdict with a label. We asked the AI to
  confirm in code; once confirmed, the AI wrote the fix (`_verdict_is_yes`)
  to our spec.
- **Edge cases we explicitly tested,** by asking the AI to run targeted
  probes against the real API: seed-2.0-lite on `b04` (negation phrasing),
  what happens under `content_filter`, what happens when `resp.usage` is
  `None` (the AI's original code crashed; we ordered the defensive guard),
  what happens when an upstream returns HTML instead of JSON
  (`json.JSONDecodeError` not caught — we ordered it added to
  `TRANSIENT_EXC`).

### Prompt design — ours

- We iterated the judge prompt multiple times. We **caught dataset leaks in
  the AI's first drafts**: the `Final Answer: 1/2` example was the `p06`
  answer; the `n!` example was the `p08` answer; the `Room 96 is messy.
  There are 12 clean rooms.` example was the `b01` answer. We ordered all
  dataset-coupled examples replaced with generic ones.
- We added the explicit `Be strict` framing and the multi-fact /
  multiple-choice rules to the judge prompt after observing under-strict
  AI-default behaviour.

### Documentation — drafted with AI assistance, finalized by us

The three documents in this submission — [README.md](README.md),
[docs/SPEC_v3.md](docs/SPEC_v3.md), and [report.md](report.md) — were
**drafted with the help of AI** under our direction:

- **We wrote the outlines.** Section structure, claims to make, which
  figures go where, what each subsection is supposed to argue — all
  ours. The AI did not propose the structure.
- **We supplied every number.** All benchmark scores, accuracy
  percentages, cost figures, cross-judge spreads, and per-cell
  observations cited in the docs come from real `details_*.json` data
  we generated, not from AI synthesis. When we asked the AI to draft a
  table, we either pasted the numbers in or asked it to read the
  committed JSON.
- **AI drafted prose; we reviewed, edited, and cut.** First-pass
  English wording was AI-generated for many paragraphs (e.g., the
  "where models succeed" / "where models fail" sections in
  [report.md](report.md), the multi-paragraph CHANGELOG entries, the
  pluggable-judge section of SPEC §2). We rewrote what wasn't
  precise, deleted what wasn't honest, and verified every concrete
  claim against the data. Examples of cuts we ordered: a "derivatives
  is structurally the hardest category" conclusion, a "per-model judge
  variance" subsection — both removed because they overclaimed.
- **We wrote the design rationale.** Sections that explain *why* a
  design choice was made (the no-tools experimental condition, the
  pluggable judge motivation, the verdict-parser bug story, why
  deepseek as canonical) reflect our reasoning. The AI summarized our
  decisions in prose; it did not author the decisions.


### Where AI was wrong and we corrected it

- **The verdict-parser bug.** AI-written code with `startswith("YES")`. We
  caught it; AI fixed to our spec.
- **Over-engineering revert.** AI added a `_no_answer_reason` /
  `_no_answer_result` / multi-mark scheme to "handle" content-filtered
  cells. We rejected: the judge already returns 0 on an empty raw response,
  so the extra layer was redundant code that obscured the simpler flow.
  We ordered the revert.
- **`resp.usage = None` crash.** AI's `_stats_from()` assumed usage was
  always present; one provider returned `None`, the run crashed. We
  diagnosed it from the traceback and ordered the defensive guard.
- **Schema-defaults bug.** AI added 12 new observability fields to `Result`
  without defaults, breaking `Result(**row)` for older JSONL rows. We hit
  it on a resume, ordered defaults on every new field.
- **Stale-partial bug in `resume_run`.** AI initially merged ALL
  `details_*.jsonl` files, including ones from older model lineups; this
  let stale data sneak into the union. We caught it (1 stale cell in run2),
  ordered the foreign-model detector that now skips stale partial files.

## 3. What the AI actually produced

| Component | AI did | We did |
|---|---|---|
| `pipeline/*.py` source code | Wrote the code per our specs; iterated on structure | Designed the architecture, reviewed every diff, demanded several rewrites and the dedup cleanup |
| The three system prompts in `pipeline/prompts.py` | First-pass wording | Specified what each prompt must do, caught the dataset leaks, added MCQ / multi-fact / strictness rules, iterated until clean |
| Entry scripts (`run_benchmark.py`, `resume_run.py`, `rerun_errors.py`, `rejudge_run.py`) | First-pass implementations | Specified CLI flags (`--label`, `--judge`), recovery semantics, and the never-overwrite rule |
| Data files (`data/*.json`) | UTF-8 mojibake cleanup, ID renumbering, JSON-schema fitting, validator | We supplied all question content; verified every expected answer ourselves; chose category composition |
| Documentation (`README.md`, `docs/SPEC_v3.md`, `docs/CHANGELOG.md`, `report.md`) | First-pass prose, table formatting, summarising our decisions into the existing doc structure, image-embedding | We wrote outlines, supplied every number from real data, reviewed/edited/cut prose, caught factual errors (e.g. stale max_tokens), and authored all design rationale and interpretive claims |

## 4. How we verified AI output

The checks that actually changed the result:

- **We ran every change against the real OpenRouter API** and inspected real
  per-cell rows in `details_*.json` — not synthetic unit tests. This is how
  we discovered `usage=None`, non-JSON response bodies, OpenRouter's
  daily-cap 403, content_filter finish_reason, and provider-specific
  `max_tokens` semantics.
- **We audited judge disagreements category by category**, which is how we
  found the parser bug.
- **The cross-judge replay** (re-grading one set of model outputs with five
  judges) is itself a verification mechanism: it showed any single-judge
  leaderboard is judge-sensitive to ~7 % of the scale, with same-vendor
  inflation in the Google judge.
- **The deterministic numeric pre-check** was validated against the cells
  where two judges already agreed before we turned it on — zero false
  positives in that calibration set.
- **We rejected AI suggestions** when they were over-engineered or
  redundant (see §2 last subsection).

## 5. Provenance and source-of-truth

We do not present any AI-generated feature or analysis as original source
truth. Specifically:

- All benchmark numbers in `report.md` come from real API calls we paid for
  and committed under `results/`. Every claim points to a file a reader can
  open and verify.
- The verdict-parser bug is flagged honestly — a bug in AI-drafted code
  that we caught while auditing the data, not something we "got right the
  first time."
- We own the design decisions, the methodology, the analyses, and the
  interpretive claims in the report. Every analysis is derived from
  committed data in `results/` that a reader can re-run.

No secrets or API keys are included in this submission; the live key lives
only in a gitignored `.env`.

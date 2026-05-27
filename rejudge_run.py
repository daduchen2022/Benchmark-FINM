#!/usr/bin/env python3
"""Re-judge every cell of an existing run with a (possibly different) judge.

Reuses each cell's preserved `raw_response` — the model under test is NOT
re-called, only the judge. Cheap (judge tokens only) and isolates the
judge effect: same model outputs, two judges => any score delta is the
judge's.

Skips cells whose `raw_response` is empty (e.g., a model-call error
during the original run). Those need a full re-run via `rerun_errors.py`
first.

Usage:
    python rejudge_run.py --details results/details_run2_judge_gemini.json \\
        --judge deepseek/deepseek-v4-pro --label run2_judge_deepseek
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from pipeline import clients
from pipeline.clients import has_api_key
from pipeline.dataset import load_questions
from pipeline.models import MODELS
from pipeline.output import write_outputs
from pipeline.runner import (
    Result, _persist_progress, _rejudge_cell,
    make_progress, row_to_result,
)


async def _rejudge_with_progress(cfg, q, prev: Result, sem, progress) -> Result:
    """Run `_rejudge_cell` through the standard progress stream + JSONL append."""
    async with sem:
        result = await _rejudge_cell(cfg, q, prev)
    await _persist_progress(result, progress)
    return result


async def main_async(details_path: Path, questions_path: Path, out_dir: Path,
                     concurrency: int, label: str) -> None:
    if not has_api_key():
        raise RuntimeError("OPENROUTER_API_KEY not set. Add it to .env.")
    rows = json.load(open(details_path))
    print(f"[rejudge] source: {details_path.name}  ({len(rows)} cells)")

    questions = load_questions(questions_path)
    models = list(MODELS)
    cfg_by_name = {m.name: m for m in models}
    q_by_id = {q["id"]: q for q in questions}

    targets, skipped = [], []
    for row in rows:
        cfg = cfg_by_name.get(row["model"])
        q = q_by_id.get(row["question_id"])
        if cfg is None or q is None:
            skipped.append((row, "model/question not in current lineup"))
            continue
        if not row.get("raw_response"):
            skipped.append((row, "empty raw_response — needs full re-run"))
            continue
        targets.append((row, cfg, q))

    print(f"[rejudge] rejudging {len(targets)} cells; skipped {len(skipped)}")
    for row, reason in skipped[:5]:
        print(f"   skip: {row['model']}/{row['question_id']} ({reason})")
    if len(skipped) > 5:
        print(f"   ... and {len(skipped) - 5} more")

    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / f"details_{label}.jsonl"
    progress = make_progress(jsonl_path, len(targets))
    sem = asyncio.Semaphore(concurrency)

    tasks = [
        _rejudge_with_progress(cfg, q, row_to_result(row), sem, progress)
        for row, cfg, q in targets
    ]
    new_results = await asyncio.gather(*tasks)

    # Merge: replace each rejudged cell, keep skipped cells as-is so the
    # output file still has all 500 rows (errors flagged on the skips).
    by_key = {(r.model, r.question_id): r for r in new_results}
    merged = [by_key.get((row["model"], row["question_id"]), row_to_result(row))
              for row in rows]

    write_outputs(merged, models, questions, out_dir, label)
    n_err = sum(1 for r in merged if r.error)
    print(f"\n[rejudge] errors in output: {n_err}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--details", required=True,
                   help="path to details_<label>.json to rejudge")
    p.add_argument("--questions", default="data")
    p.add_argument("--out", default="results")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--label", required=True,
                   help="suffix for output files (required — never overwrites).")
    p.add_argument("--judge", required=True,
                   help=f"judge model (OpenRouter id). "
                        f"Known: {', '.join(sorted(clients.KNOWN_JUDGE_PRICING))}.")
    args = p.parse_args()

    clients.set_judge(args.judge)
    print(f"[rejudge] judge: {clients.JUDGE_MODEL} "
          f"(${clients.JUDGE_PRICE_IN}/${clients.JUDGE_PRICE_OUT} per Mtok)")

    asyncio.run(main_async(
        details_path=Path(args.details),
        questions_path=Path(args.questions),
        out_dir=Path(args.out),
        concurrency=args.concurrency,
        label=args.label,
    ))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

"""Run the benchmark: every (model, question) pair, in parallel, results saved.

v3.2 pipeline:
    raw = call_model(model, question)            # the model under test answers
    if question.answer_type == "open":
        rubric_score, reasoning = judge_rubric_score(question, rubric, raw)
        score = rubric_score * RUBRIC_WEIGHT     # contribution to total
        correct = None                            # rubric questions have no binary
    else:
        correct, extracted, reasoning = judge_answer(question, expected, raw)
        score = 1.0 if correct else 0.0
"""
from __future__ import annotations

import asyncio
import csv
import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from .clients import (
    RUBRIC_WEIGHT,
    call_model, has_api_key, judge_answer, judge_rubric_score,
)
from .models import MODELS, ModelConfig


@dataclass
class Result:
    model: str
    question_id: str
    score: float                       # 0.0-1.0 contribution to the total
    correct: Optional[bool]            # binary verdict for non-rubric; None for rubric
    extracted_answer: Optional[str]    # judge's line-1 / "rubric:N/10" for rubric
    expected_answer: str               # for rubric, this is the full rubric text
    raw_response: str
    judge_reasoning: Optional[str]
    latency_s: float
    sampling_controlled: bool          # False = model ignored our temp/top_p
    tool_calls: Optional[list] = None  # v3.0: list of {tool, arguments, result}
    rubric_score: Optional[int] = None # 1-10 for answer_type=open, else None
    error: Optional[str] = None


REQUIRED_QUESTION_FIELDS = ("id", "question", "answer")


def load_questions(path: Path) -> list[dict]:
    with open(path) as f:
        qs = json.load(f)
    _validate(qs)
    return qs


def _validate(qs) -> None:
    if not isinstance(qs, list) or not qs:
        raise ValueError("questions.json must be a non-empty JSON array")
    seen = set()
    for i, q in enumerate(qs):
        missing = [k for k in REQUIRED_QUESTION_FIELDS if k not in q]
        if missing:
            raise ValueError(f"question #{i}: missing fields {missing}")
        if q["id"] in seen:
            raise ValueError(f"duplicate question id: {q['id']}")
        seen.add(q["id"])
        # answer_type / topic / difficulty / tolerance are optional metadata.


async def _eval_one(cfg: ModelConfig, q: dict, sem: asyncio.Semaphore,
                    progress: dict) -> Result:
    async with sem:
        start = time.time()
        try:
            raw, tool_log = await call_model(cfg, q["question"])
            expected = str(q["answer"])

            if q.get("answer_type") == "open":
                # `expected` here is a rubric, not a single answer.
                rubric_score, reasoning = await judge_rubric_score(
                    q["question"], expected, raw)
                score = rubric_score * RUBRIC_WEIGHT
                correct: Optional[bool] = None
                extracted = f"rubric:{rubric_score}/10"
                rubric_field: Optional[int] = rubric_score
            else:
                is_correct, extracted, reasoning = await judge_answer(
                    q["question"], expected, raw)
                score = 1.0 if is_correct else 0.0
                correct = is_correct
                rubric_field = None

            result = Result(
                model=cfg.name, question_id=q["id"],
                score=score, correct=correct,
                extracted_answer=extracted, expected_answer=expected,
                raw_response=raw, judge_reasoning=reasoning,
                latency_s=time.time() - start,
                sampling_controlled=cfg.supports_temperature,
                tool_calls=tool_log if tool_log else None,
                rubric_score=rubric_field,
            )
        except Exception as e:
            result = Result(
                model=cfg.name, question_id=q["id"],
                score=0.0, correct=False,
                extracted_answer=None, expected_answer=str(q["answer"]),
                raw_response="", judge_reasoning=None,
                latency_s=time.time() - start,
                sampling_controlled=cfg.supports_temperature,
                tool_calls=None, rubric_score=None,
                error=f"{type(e).__name__}: {e}",
            )
        progress["done"] += 1
        if result.error:
            mark = "E"
        elif result.rubric_score is not None:
            mark = f"{result.rubric_score}"      # show rubric score 0-10
        else:
            mark = "✓" if result.correct else "✗"
        print(f"  [{progress['done']:>3}/{progress['total']}] {cfg.name:25s} {q['id']:>4}  "
              f"{mark:<3} {result.latency_s:5.1f}s", flush=True)
        return result


async def run_benchmark(
    questions_path: Path,
    out_dir: Path,
    concurrency: int = 8,
) -> dict:
    if not has_api_key():
        raise RuntimeError("OPENROUTER_API_KEY not set. Add it to .env.")
    questions = load_questions(questions_path)
    models = list(MODELS)

    print(f"[runner] {len(models)} models x {len(questions)} questions "
          f"= {len(models) * len(questions)} calls")
    uncontrolled = [m.name for m in models if not m.supports_temperature]
    if uncontrolled:
        print(f"[runner] sampling NOT controlled for: {', '.join(uncontrolled)}")

    sem = asyncio.Semaphore(concurrency)
    progress = {"done": 0, "total": len(models) * len(questions)}
    tasks = [_eval_one(m, q, sem, progress) for m in models for q in questions]
    results: list[Result] = await asyncio.gather(*tasks)

    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return _write_outputs(results, models, questions, out_dir, timestamp)


def _write_outputs(results, models, questions, out_dir, timestamp):
    # 1. Full detail JSON.
    details_path = out_dir / f"details_{timestamp}.json"
    with open(details_path, "w") as f:
        json.dump([asdict(r) for r in results], f, indent=2, ensure_ascii=False)

    # Index: question_id -> topic (for per-category aggregation).
    qid_topic = {q["id"]: q.get("topic", "uncategorized") for q in questions}
    qid_order = {q["id"]: i for i, q in enumerate(questions)}

    # 2. Per-model totals + missed/error question IDs + per-category breakdown.
    totals = {}
    for m in models:
        totals[m.name] = {
            "score_total": 0.0, "total": 0, "errors": 0,
            "missed_ids": [], "error_ids": [],
            "per_category": defaultdict(lambda: {"score": 0.0, "total": 0}),
            "sampling_controlled": m.supports_temperature,
        }

    sorted_results = sorted(results, key=lambda r: qid_order.get(r.question_id, 0))
    for r in sorted_results:
        t = totals[r.model]
        t["total"] += 1
        t["score_total"] += r.score

        cat = qid_topic.get(r.question_id, "uncategorized")
        t["per_category"][cat]["score"] += r.score
        t["per_category"][cat]["total"] += 1

        if r.error:
            t["errors"] += 1
            t["error_ids"].append(r.question_id)
        elif r.score < 1.0:
            t["missed_ids"].append(r.question_id)

    # Finalize: derived metrics + convert defaultdicts to plain dicts.
    for t in totals.values():
        t["accuracy"] = t["score_total"] / t["total"] if t["total"] else 0.0
        t["per_category"] = {
            cat: {**c, "accuracy": c["score"] / c["total"] if c["total"] else 0.0}
            for cat, c in t["per_category"].items()
        }

    summary = {
        "timestamp": timestamp,
        "num_questions": len(questions),
        "num_models": len(models),
        "rubric_weight": RUBRIC_WEIGHT,
        "max_possible_score": float(len(questions)),
        "per_model": totals,
        "details_file": details_path.name,
    }
    summary_path = out_dir / f"summary_{timestamp}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 3. CSV — per-question cells show contribution (0/1 for binary, 0.0-1.0 for rubric).
    csv_path = out_dir / f"scores_{timestamp}.csv"
    qids = [q["id"] for q in questions]
    by_model = {}
    for r in results:
        by_model.setdefault(r.model, {})[r.question_id] = r
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["model"] + qids + ["score", "accuracy", "sampling_controlled"])
        sorted_models = sorted(models, key=lambda m: -totals[m.name]["score_total"])
        for m in sorted_models:
            row = [m.name]
            for qid in qids:
                r = by_model.get(m.name, {}).get(qid)
                if r is None:
                    row.append("")
                elif r.rubric_score is not None:
                    row.append(f"{r.score:.1f}")    # rubric: 0.0, 0.1, 0.2, ... 1.0
                else:
                    row.append(int(r.score))         # binary: 0 or 1
            row.append(f"{totals[m.name]['score_total']:.2f}")
            row.append(f"{totals[m.name]['accuracy']:.3f}")
            row.append("yes" if m.supports_temperature else "no")
            w.writerow(row)

    print(f"[runner] wrote {details_path.name}, {summary_path.name}, {csv_path.name}")
    return summary

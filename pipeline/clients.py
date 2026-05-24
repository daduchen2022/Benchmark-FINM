"""OpenRouter client + unified LLM-as-judge + v3.0 tool calling.

v3.0 changes vs v2.0:
 - Models under test now have access to two tools:
     - calculator(expression)  — a Python-eval-based math evaluator (function calling)
     - web search              — via OpenRouter's `plugins=[{"id":"web"}]` (RAG substitute)
 - Multi-turn tool dispatch: a model can call calculator up to MAX_TOOL_ITERATIONS
   times before producing its final answer.
 - We log every tool call (name, arguments, result) into the Result for audit.

Grading is unchanged: a single Claude Sonnet 4.6 judge call still sees
(question, expected, full raw response) and returns 3 lines.
"""
from __future__ import annotations

import asyncio
import json
import math
import os
from typing import Optional

from .models import ModelConfig


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Per single HTTP call to OpenRouter. Each tool-loop iteration is one HTTP call.
MODEL_CALL_TIMEOUT_S = 120.0
JUDGE_CALL_TIMEOUT_S = 60.0

# Hard cap on the TOTAL answering time per (model, question), across ALL tool
# iterations. After 2 minutes the runtime cancels the model's work and that
# cell is recorded as an `error: TimeoutError` row. Keeps a single slow / chatty
# model from holding up the whole run.
TOTAL_ANSWER_TIMEOUT_S = 120.0

# Cap how many calculator/tool iterations a single model can do per question.
MAX_TOOL_ITERATIONS = 8


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
MODEL_SYSTEM_PROMPT = (
    "You are answering a quantitative-finance interview question. Think step by step. "
    "You have access to a `calculator` tool for arithmetic and to live web search "
    "(used automatically by the runtime when helpful). Use these tools whenever "
    "they reduce error. After your reasoning, clearly state your final answer at the end."
)

JUDGE_MODEL = "anthropic/claude-sonnet-4.6"

# Weight applied to rubric scores so they line up with binary 0/1 scoring.
#   contribution_to_total = rubric_score * RUBRIC_WEIGHT     (so 10/10 -> 1.0)
# This number is tied to the 1-10 rubric scale; if you change the rubric scale
# in the judge prompt below, update this so max contribution stays 1.0.
RUBRIC_WEIGHT = 0.1

JUDGE_SYSTEM_PROMPT = (
    "你是一个评分助手。给你一道题、标准答案、以及某个模型的完整回复，"
    "你判断模型回复中最终给出的答案是否正确。\n"
    "\n"
    "判定原则：\n"
    "1. 看模型最终结论，而不是中间推理。如果中间算出了正确答案但最终改成别的，按最终的判。\n"
    "2. 容忍合理的表达差异：\n"
    "   - 数值：'0.667' ≈ '0.6667' ≈ '2/3' ≈ '66.7%'（合理误差内等价）\n"
    "   - 数学符号：'√5' ≈ '2.236' ≈ 'sqrt(5)' ≈ '\\sqrt{5}'\n"
    "   - 分数：'1/4' ≈ '0.25' ≈ '25%'\n"
    "   - 公式：'2^(n-1)/(2^n-1)' ≈ '(2^(n-1))/(2^n - 1)' ≈ latex 形式\n"
    "   - 时间：'11:23am' ≈ '11:23' ≈ '37 minutes before noon'\n"
    "   - 语义：'down' ≈ 'decreases' ≈ 'the water level falls'\n"
    "3. 如果题目问多个东西（例如同时问 with/without replacement），模型只要把标准答案对应的那部分答对即可。\n"
    "4. 如果模型没给出可识别的最终答案，extracted 写 'N/A'，verdict 写 NO。\n"
    "\n"
    "输出格式（严格 3 行，不要其他内容）：\n"
    "第 1 行：模型给出的最终答案（简短，≤30 字，仅事实，不要解释）\n"
    "第 2 行：判定理由（≤30 字）\n"
    "第 3 行：YES 或 NO（仅这两个词之一）"
)


# Rubric judge — used only when answer_type == "open". The `expected` field
# in this path is NOT a single answer; it is a multi-criterion rubric written
# by the dataset author. Judge scores model's response 1-10 against it.
RUBRIC_JUDGE_SYSTEM_PROMPT = (
    "你是一个严格的 open question 评分员。你会收到：一道开放题、一份分级 rubric、"
    "以及某个模型的完整回复。你按照 rubric 给模型回复打 1-10 分。\n"
    "\n"
    "通用打分锚点（rubric 中如有具体定义，以 rubric 为准）：\n"
    "  1-3 分：完全没切中要点 / 事实错误 / 文不对题 / 没有有效内容\n"
    "  4-6 分：部分切中 rubric 核心点，但有明显遗漏或错误\n"
    "  7-8 分：主要 rubric 要点都答到了，论述基本清晰，有少量缺失\n"
    "  9-10 分：完整覆盖 rubric 要点，论述清晰准确，无明显问题\n"
    "\n"
    "判分原则：\n"
    "1. 严格按 rubric 衡量。rubric 没要求的『附加观点』不加分。\n"
    "2. 看模型最终结论 + 关键推理。流水账中间过程不加分。\n"
    "3. 没给出可识别答案 / 完全跑题 → 1-2 分。\n"
    "4. 默认偏严，不要分数膨胀。\n"
    "\n"
    "输出格式（严格 3 行，不要其他内容）：\n"
    "第 1 行：模型回答的核心要点摘要（≤30 字）\n"
    "第 2 行：打分理由（≤60 字，说明哪些 rubric 要点命中 / 遗漏）\n"
    "第 3 行：一个 1 到 10 的整数（仅一个数字，不带其他字符）"
)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
CALCULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "calculator",
        "description": (
            "Evaluate a single Python-style math expression and return the numerical result. "
            "Supports +, -, *, /, **, parentheses. Functions: sqrt, log (natural), ln, log2, log10, "
            "exp, sin, cos, tan, factorial, comb (binomial coefficient), perm, ceil, floor, abs, "
            "round, min, max, pow, sum. Constants: pi, e. "
            "Example expressions: 'sqrt(5)', 'comb(10,2)/comb(52,2)', '(2/3)**10'."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Math expression to evaluate.",
                }
            },
            "required": ["expression"],
        },
    },
}

# OpenRouter's universal web search plugin. Acts as our RAG substitute since
# no project corpus exists. Note: adds ~$0.004 per call.
WEB_PLUGIN = {"id": "web", "max_results": 5}

_SAFE_CALC_NAMES = {
    "abs": abs, "min": min, "max": max, "round": round, "pow": pow, "sum": sum,
    "sqrt": math.sqrt, "log": math.log, "ln": math.log,
    "log2": math.log2, "log10": math.log10,
    "exp": math.exp, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "pi": math.pi, "e": math.e,
    "factorial": math.factorial, "comb": math.comb, "perm": math.perm,
    "ceil": math.ceil, "floor": math.floor,
}


def _safe_calc(expression: str) -> str:
    """Evaluate `expression` in a restricted namespace. Returns numeric result as string,
    or 'Error: ...' on any failure. Blocks obvious sandbox-escape tokens."""
    if not isinstance(expression, str) or not expression.strip():
        return "Error: empty expression"
    bad = ("__", "import", "open(", "exec(", "compile(", "eval(", "globals", "locals")
    if any(tok in expression for tok in bad):
        return "Error: forbidden token in expression"
    try:
        val = eval(expression, {"__builtins__": {}}, _SAFE_CALC_NAMES)   # noqa: S307
    except Exception as e:
        return f"Error: {type(e).__name__}: {e}"
    return str(val)


# ---------------------------------------------------------------------------
# Client (lazy singleton)
# ---------------------------------------------------------------------------
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    from openai import AsyncOpenAI   # lazy import
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set. Add it to .env.")

    _client = AsyncOpenAI(
        api_key=api_key,
        base_url=OPENROUTER_BASE_URL,
        timeout=MODEL_CALL_TIMEOUT_S,
        default_headers={
            "HTTP-Referer": os.environ.get("OPENROUTER_REFERER", ""),
            "X-Title":      os.environ.get("OPENROUTER_TITLE", "Quant Interview Benchmark"),
        },
    )
    return _client


# ---------------------------------------------------------------------------
# Model call with tool dispatch
# ---------------------------------------------------------------------------
async def call_model(cfg: ModelConfig, prompt: str) -> tuple[str, list]:
    """Public entry. Caps total answering time at TOTAL_ANSWER_TIMEOUT_S (2 min in v3.0).
    On timeout, asyncio.TimeoutError propagates and the runner records that cell
    as an `error` row."""
    return await asyncio.wait_for(
        _call_model_inner(cfg, prompt),
        timeout=TOTAL_ANSWER_TIMEOUT_S,
    )


async def _call_model_inner(cfg: ModelConfig, prompt: str) -> tuple[str, list]:
    """v3.0 call body: the model can iteratively use the calculator tool and
    benefits from OpenRouter's web-search plugin (RAG substitute).

    Returns (final_text, tool_calls_log).
    """
    client = _get_client()
    messages: list = [
        {"role": "system", "content": MODEL_SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ]
    tool_log: list = []
    last_content = ""

    for _ in range(MAX_TOOL_ITERATIONS):
        resp = await client.chat.completions.create(
            model=cfg.model_id,
            temperature=0,
            top_p=1.0,
            max_tokens=8192,
            messages=messages,
            tools=[CALCULATOR_TOOL],
            tool_choice="auto",
            extra_body={"plugins": [WEB_PLUGIN]},
        )
        choice = resp.choices[0]
        msg = choice.message
        last_content = msg.content or ""

        # No tool calls -> we're done.
        if not getattr(msg, "tool_calls", None):
            return last_content, tool_log

        # Append the assistant message that contained tool_calls.
        try:
            messages.append(msg.model_dump(exclude_none=True))
        except Exception:
            # Fall back to a minimal dict if the SDK shape is unexpected.
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name,
                                  "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            })

        # Execute each tool call and append the result.
        for tc in msg.tool_calls:
            name = tc.function.name
            args_raw = tc.function.arguments or "{}"
            try:
                args = json.loads(args_raw)
            except json.JSONDecodeError:
                args = {}
            if name == "calculator":
                result = _safe_calc(args.get("expression", ""))
            else:
                result = f"Error: unknown tool {name!r}"

            tool_log.append({"tool": name, "arguments": args_raw, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    # Hit iteration cap — return whatever the last assistant message was.
    return (last_content or "[max tool iterations reached]"), tool_log


# ---------------------------------------------------------------------------
# Judge (unchanged from v2.0)
# ---------------------------------------------------------------------------
async def judge_answer(question: str, expected: str, raw_response: str) -> tuple[bool, str, str]:
    """LLM-as-judge for everything. One call decides extraction + correctness.

    Returns (is_correct, extracted_answer, full_judge_text).
    """
    if not raw_response or not raw_response.strip():
        return False, "N/A", "model returned empty response"

    client = _get_client().with_options(timeout=JUDGE_CALL_TIMEOUT_S)
    raw_excerpt = raw_response[-4000:] if len(raw_response) > 4000 else raw_response

    resp = await client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        top_p=1.0,
        max_tokens=200,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"题目：\n{question}\n\n"
                f"标准答案：{expected}\n\n"
                f"模型回复（完整，可能截尾）：\n{raw_excerpt}"
            )},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    if len(lines) >= 3:
        verdict = lines[-1].upper()
    elif len(lines) == 2:
        verdict = lines[1].upper()
    elif len(lines) == 1:
        verdict = lines[0].upper()
    else:
        verdict = ""

    if len(lines) >= 1:
        extracted = lines[0]
    else:
        extracted = "N/A"

    is_correct = verdict.startswith("YES")
    return is_correct, extracted, text


async def judge_rubric_score(question: str, rubric: str,
                             raw_response: str) -> tuple[int, str]:
    """For answer_type='open': score model's reply against `rubric` on 1-10 scale.

    Returns (score, full_judge_text). On parse failure returns (0, judge_text).
    """
    if not raw_response or not raw_response.strip():
        return 0, "model returned empty response"

    client = _get_client().with_options(timeout=JUDGE_CALL_TIMEOUT_S)
    raw_excerpt = raw_response[-4000:] if len(raw_response) > 4000 else raw_response

    resp = await client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        top_p=1.0,
        max_tokens=300,
        messages=[
            {"role": "system", "content": RUBRIC_JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": (
                f"题目：\n{question}\n\n"
                f"评分 Rubric：\n{rubric}\n\n"
                f"模型回复（完整，可能截尾）：\n{raw_excerpt}"
            )},
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Extract integer 1-10 from the last line (be tolerant of stray punctuation).
    import re
    score = 0
    if lines:
        m = re.search(r"\b(10|[1-9])\b", lines[-1])
        if m:
            score = int(m.group(1))
    score = max(0, min(10, score))   # clamp defensively
    return score, text


def has_api_key() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))

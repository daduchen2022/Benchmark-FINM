"""All custom exceptions used by the pipeline live here.

These are exceptions we *expect* and recover from at the cell level — every
one of them, when raised inside `_eval_one`, causes the affected
(model, question) cell to be recorded as `error` in the Result row, and
the rest of the run continues.

Anything *not* in this file (KeyError, AttributeError, etc.) is treated
as a pipeline bug and propagates so it surfaces loudly.

The `TRANSIENT_EXC` tuple is the single source of truth — `runner.py`
imports it directly into its try/except.
"""
from __future__ import annotations

import json

import openai


class BinaryJudgeParseError(RuntimeError):
    """Binary judge returned an empty / unparseable reply.

    Typical cause: the judge is a reasoning model that spent its entire
    `max_tokens` budget on internal reasoning before producing any visible
    output. The cell is recorded as a re-runnable error rather than
    silently scoring 0.
    """


class RubricJudgeParseError(RuntimeError):
    """Rubric judge's reply has no parseable JSON, malformed JSON, or empty
    `scores` list. Same recovery semantics as `BinaryJudgeParseError`."""


class EmptyChoicesError(RuntimeError):
    """OpenRouter returned a 200 OK but `choices` was null / empty.

    Happens occasionally when an upstream provider applies a silent
    content filter that the SDK doesn't surface as a normal API error.
    """


# Tuple consumed by runner._eval_one's try/except. Order doesn't matter.
TRANSIENT_EXC: tuple[type[Exception], ...] = (
    BinaryJudgeParseError,
    RubricJudgeParseError,
    EmptyChoicesError,
    # openai.APIError covers all SDK-wrapped network / status errors, including
    # APITimeoutError, RateLimitError, BadRequestError, PermissionDeniedError.
    openai.APIError,
    # Some upstream providers occasionally return HTML / plain-text error pages
    # instead of JSON. The SDK lets the bare JSONDecodeError bubble up — we
    # catch it here as a transient cell-level error.
    json.JSONDecodeError,
)

"""Model registry — every call routed through OpenRouter (one API key, one base URL).

The lineup mixes 2026-era frontier models with three deliberately weaker /
older baselines (`gpt-4o`, `claude-3-haiku`, `gemini-2.5-flash`) so we can see
the gap between SOTA and yesterday's models on the same questions.

For each model we record whether OpenRouter's catalog says it accepts
`temperature` / `top_p`. Some reasoning models (e.g. `openai/gpt-5.5`) don't
— OpenRouter silently drops those params, so our "temperature=0 for
everyone" promise doesn't actually hold for them. We surface this in the
Result so the comparison can be qualified.

Pricing is `$ per million tokens` (prompt / completion), verified against
OpenRouter on 2026-05-26. Update when re-pricing happens. Used to compute
per-cell `model_cost_usd` in the Result; the pipeline still runs (with
cost = 0) if a row's pricing is left at 0.

The `name` field is the display label used in CSV/JSON outputs.
The `model_id` field is OpenRouter's identifier.
"""
from dataclasses import dataclass


@dataclass
class ModelConfig:
    name: str                          # display name in results
    model_id: str                      # OpenRouter model ID
    supports_temperature: bool = True  # if False, temp/top_p are silently dropped
    price_in: float = 0.0              # $ / 1M prompt tokens
    price_out: float = 0.0             # $ / 1M completion tokens (includes reasoning)


MODELS = [
    # Frontier / 2026-era
    ModelConfig("seed-2.0-lite",           "bytedance-seed/seed-2.0-lite",                                 price_in=0.250, price_out=2.000),
    ModelConfig("claude-sonnet-4.6",       "anthropic/claude-sonnet-4.6",                                  price_in=3.000, price_out=15.000),
    ModelConfig("gpt-5.5",                 "openai/gpt-5.5",                    supports_temperature=False, price_in=5.000, price_out=30.000),
    ModelConfig("gemini-3.1-flash-lite",   "google/gemini-3.1-flash-lite",                                 price_in=0.250, price_out=1.500),
    ModelConfig("grok-4.3",                "x-ai/grok-4.3",                                                price_in=1.250, price_out=2.500),
    ModelConfig("qwen3.6-flash",           "qwen/qwen3.6-flash",                                           price_in=0.188, price_out=1.125),
    ModelConfig("deepseek-v4-flash",       "deepseek/deepseek-v4-flash",                                   price_in=0.100, price_out=0.200),
    # Older / weaker baselines — for SOTA comparison
    ModelConfig("gpt-4o",                  "openai/gpt-4o",                                                price_in=2.500, price_out=10.000),
    ModelConfig("claude-3-haiku",          "anthropic/claude-3-haiku",                                     price_in=0.250, price_out=1.250),
    ModelConfig("gemini-2.5-flash",        "google/gemini-2.5-flash",                                      price_in=0.300, price_out=2.500),
]

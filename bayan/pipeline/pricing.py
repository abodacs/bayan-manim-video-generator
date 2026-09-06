"""Cost estimation for LLM calls.

Price constants are USD per 1M tokens, keyed by model name. These numbers are
estimates recorded in run records -- never an invoice. Models without
published pricing here estimate to 0.0; extend the table as pricing becomes
available.
"""

from __future__ import annotations

from bayan.pipeline.models import TokenUsage

PRICE_TABLE_USD_PER_1M: dict[str, tuple[float, float]] = {
    # model: (input USD per 1M tokens, output USD per 1M tokens)
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
}


def estimate_cost_usd(model: str, usage: TokenUsage | None) -> float:
    """Estimate the USD cost of one LLM call from its token usage."""
    if usage is None:
        return 0.0
    prices = PRICE_TABLE_USD_PER_1M.get(model)
    if prices is None:
        return 0.0
    input_cost = usage.prompt_tokens * prices[0] / 1_000_000
    output_cost = usage.completion_tokens * prices[1] / 1_000_000
    return input_cost + output_cost

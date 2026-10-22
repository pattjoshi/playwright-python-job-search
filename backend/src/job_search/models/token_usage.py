"""What the AI calls of one run used (for the cost shown in the UI)."""

from dataclasses import dataclass


@dataclass
class TokenUsage:
    calls: int = 0
    input_tokens: int = 0  # includes cached_tokens
    cached_tokens: int = 0  # input tokens OpenAI served from its prompt cache (cheaper)
    output_tokens: int = 0

    def cost_usd(
        self, input_price: float | None, output_price: float | None, cached_price: float | None = None
    ) -> float | None:
        """Estimated cost with prices in USD per 1M tokens; None when prices aren't configured."""
        if input_price is None or output_price is None:
            return None
        cached_price = input_price if cached_price is None else cached_price
        uncached = self.input_tokens - self.cached_tokens
        return (uncached * input_price + self.cached_tokens * cached_price + self.output_tokens * output_price) / 1_000_000

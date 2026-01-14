"""Pricing configuration for different AI models."""

from decimal import Decimal
from typing import Dict, Tuple

# Preços em USD por 1M tokens (input, output)
MODEL_PRICING: Dict[str, Tuple[Decimal, Decimal]] = {
    # Claude 4.5 models
    "opus-4.5": (Decimal("15.00"), Decimal("75.00")),
    "sonnet-4.5": (Decimal("3.00"), Decimal("15.00")),
    "haiku-4.5": (Decimal("0.25"), Decimal("1.25")),

    # Gemini 3 models
    "gemini-3-pro": (Decimal("1.25"), Decimal("5.00")),
    "gemini-3-flash": (Decimal("0.075"), Decimal("0.30")),
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> Decimal:
    """Calcula custo baseado no modelo e tokens.

    Args:
        model: Nome do modelo utilizado
        input_tokens: Quantidade de tokens de entrada
        output_tokens: Quantidade de tokens de saída

    Returns:
        Custo total em USD como Decimal
    """
    if model not in MODEL_PRICING:
        return Decimal("0")

    input_price, output_price = MODEL_PRICING[model]

    # Converter tokens para milhões e calcular
    input_cost = (Decimal(input_tokens) / 1_000_000) * input_price
    output_cost = (Decimal(output_tokens) / 1_000_000) * output_price

    return input_cost + output_cost

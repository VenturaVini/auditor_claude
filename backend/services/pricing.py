"""Estimativa de custo por resposta (USD por 1M de tokens).

Preços de tabela pública dos provedores. Modelos fora do mapa retornam None
(a UI mostra só os tokens). Match por prefixo mais longo — cobre aliases e
snapshots datados (ex.: gpt-4o-mini-2024-07-18 casa com gpt-4o-mini).
"""

# (input_usd_per_1M, output_usd_per_1M)
_PRICES = {
    # Anthropic
    "claude-fable-5": (10.0, 50.0),
    "claude-opus-4": (5.0, 25.0),       # opus-4-5/4-6/4-7/4-8
    "claude-sonnet-4": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    # OpenAI (famílias com preço público estável)
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.0),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.0, 8.0),
    "gpt-4-turbo": (10.0, 30.0),
    "gpt-4": (30.0, 60.0),
    "gpt-3.5-turbo": (0.50, 1.50),
}


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    if not model:
        return None
    best = None
    for prefix in _PRICES:
        if model.startswith(prefix) and (best is None or len(prefix) > len(best)):
            best = prefix
    if best is None:
        return None
    pin, pout = _PRICES[best]
    return (input_tokens * pin + output_tokens * pout) / 1_000_000

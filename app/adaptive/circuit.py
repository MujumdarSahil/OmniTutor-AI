# =============================================================================
# app/adaptive/circuit.py — Circuit breaker: skip provider when open
# =============================================================================
# Rules: 3 failures within 60 seconds → open circuit for 60 seconds.
# When open, router skips provider (routing_reason = "circuit_open").
# After cooldown, provider is allowed again.
# =============================================================================

from app.adaptive.metrics import get_provider_metrics


def should_skip_provider(provider: str) -> bool:
    return get_provider_metrics(provider).is_circuit_open()

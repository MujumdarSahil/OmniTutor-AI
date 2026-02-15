# =============================================================================
# app/llms/router.py — Multi-LLM routing with circuit breaker and adaptive scoring
# =============================================================================

import asyncio
import time
from typing import Literal

from app.adaptive.circuit import should_skip_provider
from app.adaptive.metrics import get_provider_metrics
from app.core.config import get_settings
from app.core.providers import PROVIDERS
from app.llms.gemini_client import GeminiClient
from app.llms.groq_client import GroqClient
from app.llms.ollama_client import OllamaClient
from app.llms.openai_client import OpenAIClient
from app.utils.logger import logger

Provider = Literal["openai", "groq", "gemini", "ollama", "auto"]

# Default models when client sends empty model (free-tier friendly)
PROVIDER_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "groq": "llama-3.1-8b-instant",
    "gemini": "gemini-1.5-flash",
    "ollama": "llama3.2",
}

AUTO_MATH_KEYWORDS = ["math", "equation", "derivative", "integral", "quantum"]
AUTO_PROMPT_LONG_THRESHOLD = 8000
AUTO_PROMPT_SHORT_THRESHOLD = 2000

# Adaptive score weights
SCORE_FAILURE_WEIGHT = 0.5
SCORE_LATENCY_WEIGHT = 0.3
SCORE_REASONING_WEIGHT = 0.2


def get_client(provider: Literal["openai", "groq", "gemini", "ollama"]):
    if provider == "openai":
        return OpenAIClient()
    if provider == "groq":
        return GroqClient()
    if provider == "gemini":
        return GeminiClient()
    if provider == "ollama":
        return OllamaClient()
    raise ValueError(f"Unknown provider: {provider}")


def _compute_provider_score(provider: str) -> float:
    m = get_provider_metrics(provider)
    reasoning_weight = PROVIDERS.get(provider, {}).get("reasoning_weight", 0.5)
    failure_component = (1 - m.failure_rate) * SCORE_FAILURE_WEIGHT
    latency_component = (1.0 / (m.avg_latency + 1.0)) * SCORE_LATENCY_WEIGHT
    reasoning_component = reasoning_weight * SCORE_REASONING_WEIGHT
    return failure_component + latency_component + reasoning_component


async def _resolve_auto_provider(
    prompt: str,
) -> tuple[Literal["openai", "groq", "gemini", "ollama"], str, float | None, bool]:
    ollama_client = OllamaClient()
    ollama_reachable = await ollama_client.check_reachable()
    try:
        await ollama_client.close()
    except Exception:
        pass

    candidates: list[Literal["openai", "groq", "gemini", "ollama"]] = [
        "openai",
        "groq",
        "gemini",
        "ollama",
    ]
    available = [
        p
        for p in candidates
        if not should_skip_provider(p)
        and (p != "ollama" or ollama_reachable)
    ]

    if not available:
        return "ollama", "circuit_fallback", None, True

    best_provider: Literal["openai", "groq", "gemini", "ollama"] = available[0]
    best_score = _compute_provider_score(best_provider)
    for p in available[1:]:
        s = _compute_provider_score(p)
        if s > best_score:
            best_score = s
            best_provider = p

    return best_provider, "adaptive", best_score, False


async def generate_with_fallback(
    provider: Provider,
    model: str,
    prompt: str,
    temperature: float,
) -> tuple[str, str, float, str, str, float | None, bool]:
    original_provider: str = provider if provider != "auto" else "auto"
    effective_provider: Literal["openai", "groq", "gemini", "ollama"]
    routing_reason: str
    adaptive_score_used: float | None = None
    circuit_triggered: bool = False

    if provider == "auto":
        effective_provider, routing_reason, adaptive_score_used, circuit_triggered = (
            await _resolve_auto_provider(prompt)
        )
    else:
        effective_provider = provider
        routing_reason = "explicit"
        if should_skip_provider(effective_provider):
            circuit_triggered = True
            routing_reason = "circuit_open"
            ollama_client = OllamaClient()
            ollama_reachable = await ollama_client.check_reachable()
            try:
                await ollama_client.close()
            except Exception:
                pass
            if ollama_reachable:
                effective_provider = "ollama"
                routing_reason = "circuit_open_fallback"

    effective_model = (model or "").strip() or PROVIDER_DEFAULT_MODELS.get(
        effective_provider, "gemini-1.5-flash"
    )
    timeout = get_settings().request_timeout
    client = get_client(effective_provider)
    start = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            client.generate(prompt, effective_model, temperature),
            timeout=timeout,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        get_provider_metrics(effective_provider).record_success(latency_ms)
        logger.info(
            "llm_used",
            extra={
                "original_provider": original_provider,
                "final_provider_used": effective_provider,
                "routing_reason": routing_reason,
                "latency_ms": latency_ms,
            },
        )
        return (
            result,
            effective_provider,
            latency_ms,
            original_provider,
            routing_reason,
            adaptive_score_used,
            circuit_triggered,
        )
    except Exception as e:
        get_provider_metrics(effective_provider).record_failure()
        logger.warning(
            "provider_failed",
            extra={"provider": effective_provider, "error": str(e)},
        )
        try:
            await client.close()
        except Exception:
            pass

    fallback = OllamaClient()
    fallback_model = (model or "").strip() or PROVIDER_DEFAULT_MODELS.get("ollama", "llama3.2")
    start = time.perf_counter()
    try:
        result = await asyncio.wait_for(
            fallback.generate(prompt, fallback_model, temperature),
            timeout=timeout,
        )
        latency_ms = (time.perf_counter() - start) * 1000
        get_provider_metrics("ollama").record_success(latency_ms)
        logger.info(
            "llm_used",
            extra={
                "original_provider": original_provider,
                "final_provider_used": "ollama",
                "routing_reason": "fallback",
                "latency_ms": latency_ms,
            },
        )
        return (
            result,
            "ollama",
            latency_ms,
            original_provider,
            "fallback",
            adaptive_score_used,
            circuit_triggered,
        )
    finally:
        if hasattr(fallback, "close") and callable(fallback.close):
            await fallback.close()

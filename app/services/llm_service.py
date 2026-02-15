from app.db.session import _infer_category, insert_log
from app.llms.router import Provider, generate_with_fallback
from app.rag.index import index_count
from app.rag.retriever import retrieve_top_k_async
from app.utils.logger import logger
from app.utils.token_estimator import estimate_tokens

RAG_TOP_K = 3


async def generate(
    provider: Provider,
    model: str,
    prompt: str,
    temperature: float,
    risk_score: float | None = None,
    fingerprint: str | None = None,
) -> tuple[str, str, float]:
    effective_prompt = prompt
    rag_used = False
    if index_count() > 0:
        chunks = await retrieve_top_k_async(prompt, k=RAG_TOP_K)
        if chunks:
            context = "\n".join(chunks)
            effective_prompt = f"Context:\n{context}\n\nUser:\n{prompt}"
            rag_used = True
    logger.info("rag_used" if rag_used else "rag_skipped", extra={"rag_used": rag_used})
    (
        result,
        provider_used,
        latency_ms,
        original_provider,
        routing_reason,
        adaptive_score_used,
        circuit_triggered,
    ) = await generate_with_fallback(
        provider=provider,
        model=model,
        prompt=effective_prompt,
        temperature=temperature,
    )
    prompt_tokens = estimate_tokens(effective_prompt)
    insert_log(
        provider=provider_used,
        model=model,
        prompt_length=prompt_tokens,
        latency_ms=latency_ms,
        original_provider=original_provider,
        routing_reason=routing_reason,
        rag_used=rag_used,
        risk_score=risk_score,
        fingerprint=fingerprint,
        adaptive_score_used=adaptive_score_used,
        circuit_triggered=circuit_triggered,
        prompt_preview=prompt[:300] if prompt else None,
        category=_infer_category(prompt),
    )
    return result, provider_used, latency_ms, routing_reason

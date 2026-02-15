import asyncio
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request

from app.adaptive.metrics import PROVIDER_STATS
from app.core.config import get_settings
from app.db.models import init_db
from app.db.session import get_db_connection, get_dashboard_stats, get_last_logs
from app.rag.embeddings import get_embedding_model
from app.rag.index import index_count
from app.rag.ingest import ingest_text
from app.schemas.request import GenerateRequest
from app.schemas.response import GenerateResponse
from app.security.analyzer import analyze_prompt
from app.security.rate_guard import make_fingerprint
from app.services.llm_service import generate

# Free-tier friendly: lower rate limit to avoid provider 429
RATE_LIMIT_REQUESTS = 15
RATE_LIMIT_WINDOW_SEC = 60
_rate_store: dict[str, list[float]] = {}
_rate_lock = asyncio.Lock()


async def check_ollama_reachable() -> bool:
    try:
        base = get_settings().ollama_base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{base}/api/tags")
            return r.status_code == 200
    except Exception:
        return False


def check_db_connected() -> bool:
    try:
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def _provider_status(ollama_ok: bool) -> dict[str, str]:
    s = get_settings()
    return {
        "openai": "configured" if (s.openai_api_key and s.openai_api_key.strip()) else "missing_key",
        "groq": "configured" if (s.groq_api_key and s.groq_api_key.strip()) else "missing_key",
        "gemini": "configured" if (s.gemini_api_key and s.gemini_api_key.strip()) else "missing_key",
        "ollama": "reachable" if ollama_ok else "unreachable",
    }


MAX_PROMPT_LENGTH = 20_000


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Multi-LLM Orchestrator", lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "OmniTutor API", "docs": "/docs", "health": "/health", "generate": "POST /generate"}


@app.get("/health")
async def get_health():
    db_ok = check_db_connected()
    ollama_ok = await check_ollama_reachable()
    providers = _provider_status(ollama_ok)
    if not db_ok:
        status = "unhealthy"
    elif ollama_ok:
        status = "ok"
    else:
        status = "degraded"
    database = "connected" if db_ok else "failed"
    return {
        "status": status,
        "database": database,
        "providers": providers,
    }


async def rate_limit_check(ip: str) -> None:
    async with _rate_lock:
        now = time.monotonic()
        if ip not in _rate_store:
            _rate_store[ip] = []
        timestamps = _rate_store[ip]
        timestamps[:] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW_SEC]
        if len(timestamps) >= RATE_LIMIT_REQUESTS:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        timestamps.append(now)


@app.get("/rag/stats")
async def get_rag_stats() -> dict:
    return {"chunks_indexed": index_count()}


@app.post("/rag/ingest")
async def post_rag_ingest(body: dict) -> dict:
    text = body.get("text", "") or ""
    chunks_indexed = await ingest_text(text)
    return {"chunks_indexed": chunks_indexed}


@app.get("/admin/logs")
async def get_admin_logs() -> list:
    return get_last_logs(20)


@app.get("/dashboard/stats")
async def get_dashboard_stats_route() -> dict:
    """Daily usage and question categories for dashboard."""
    return get_dashboard_stats()


@app.get("/metrics/providers")
async def get_metrics_providers() -> dict:
    return {
        name: m.to_dict()
        for name, m in PROVIDER_STATS.items()
    }


@app.post("/generate", response_model=GenerateResponse)
async def post_generate(request: Request, body: GenerateRequest) -> GenerateResponse:
    if len(body.prompt) > MAX_PROMPT_LENGTH:
        raise HTTPException(status_code=413, detail="Prompt exceeds maximum length")
    client_host = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else client_host
    user_agent = request.headers.get("user-agent", "") or ""
    fingerprint = make_fingerprint(ip, user_agent, len(body.prompt))
    risk_score = analyze_prompt(body.prompt)
    await rate_limit_check(ip)
    try:
        response_text, provider_used, latency_ms, routing_reason = await generate(
            provider=body.provider,
            model=body.model,
            prompt=body.prompt,
            temperature=body.temperature,
            risk_score=risk_score,
            fingerprint=fingerprint,
        )
        return GenerateResponse(
            provider_used=provider_used,
            response=response_text,
            latency_ms=round(latency_ms, 2),
            routing_reason=routing_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        if "connection" in msg.lower() or "unreachable" in msg.lower() or "timeout" in msg.lower():
            raise HTTPException(status_code=502, detail="LLM provider unreachable. Check API keys and network.")
        raise HTTPException(status_code=500, detail=msg)

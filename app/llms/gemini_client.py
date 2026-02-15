# =============================================================================
# app/llms/gemini_client.py — Google Gemini API client
# =============================================================================
# Uses GEMINI_API_KEY. Suitable models: gemini-1.5-flash, gemini-1.5-pro,
# gemini-2.0-flash-exp. Default when model not Gemini-style: gemini-1.5-flash.
# Free tier: one retry on 502/429, longer timeout via REQUEST_TIMEOUT.
# =============================================================================

import asyncio
import httpx

from app.core.config import get_settings
from app.core.security import require_gemini_key
from app.llms.base import BaseLLM

GEMINI_DEFAULT_MODEL = "gemini-1.5-flash"
RETRY_STATUSES = (429, 502)


def _resolve_gemini_model(model: str) -> str:
    if not model or not model.strip():
        return GEMINI_DEFAULT_MODEL
    m = model.strip().lower()
    if m.startswith("gemini-"):
        return model.strip()
    return GEMINI_DEFAULT_MODEL


class GeminiClient(BaseLLM):
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            # Free tier: use longer timeout (env REQUEST_TIMEOUT, e.g. 60)
            timeout = max(get_settings().request_timeout, 45)
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def check_reachable(self) -> bool:
        try:
            key = require_gemini_key()
            client = await self._get_client()
            r = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_DEFAULT_MODEL}?key={key}",
                timeout=5.0,
            )
            return r.status_code == 200
        except Exception:
            return False

    async def generate(self, prompt: str, model: str, temperature: float) -> str:
        key = require_gemini_key()
        resolved_model = _resolve_gemini_model(model)
        client = await self._get_client()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{resolved_model}:generateContent?key={key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": min(2.0, max(0.0, temperature)),
                "maxOutputTokens": 8192,
            },
        }
        last_error = None
        for attempt in range(2):
            try:
                r = await client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    return ""
                first = candidates[0]
                content = first.get("content") or {}
                parts = content.get("parts") or []
                if not parts:
                    return ""
                return (parts[0].get("text") or "").strip()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 400:
                    raise ValueError(f"Gemini model or request invalid: {(e.response.text or '')[:500]}") from e
                if e.response.status_code in (401, 403):
                    raise ValueError("GEMINI_API_KEY invalid or not allowed") from e
                if e.response.status_code in RETRY_STATUSES and attempt == 0:
                    await asyncio.sleep(2.0)
                    continue
                raise ValueError(f"Gemini API error {e.response.status_code}: {(e.response.text or '')[:500]}") from e
            except httpx.RequestError as e:
                last_error = e
                if attempt == 0:
                    await asyncio.sleep(2.0)
                    continue
                raise ValueError(f"Gemini API unreachable: {e!s}") from e
        if last_error:
            if isinstance(last_error, httpx.HTTPStatusError):
                raise ValueError(f"Gemini API error {last_error.response.status_code}") from last_error
            raise ValueError(f"Gemini API unreachable: {last_error!s}") from last_error
        return ""

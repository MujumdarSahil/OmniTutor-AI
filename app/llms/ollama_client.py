import httpx

from app.core.config import get_settings
from app.llms.base import BaseLLM


class OllamaClient(BaseLLM):
    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None
        self._base_url = get_settings().ollama_base_url.rstrip("/")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=get_settings().request_timeout)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def generate(self, prompt: str, model: str, temperature: float) -> str:
        client = await self._get_client()
        r = await client.post(
            f"{self._base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature},
            },
        )
        r.raise_for_status()
        data = r.json()
        return data.get("response", "")

    async def check_reachable(self) -> bool:
        try:
            client = await self._get_client()
            r = await client.get(f"{self._base_url}/api/tags")
            return r.status_code == 200
        except Exception:
            return False

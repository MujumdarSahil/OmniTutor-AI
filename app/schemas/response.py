from pydantic import BaseModel


class GenerateResponse(BaseModel):
    provider_used: str
    response: str
    latency_ms: float
    routing_reason: str | None = None

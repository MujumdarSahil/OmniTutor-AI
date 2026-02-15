from typing import Literal

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    provider: Literal["openai", "groq", "gemini", "ollama", "auto"] = "auto"
    model: str = Field("", min_length=0)  # empty = server picks per provider
    prompt: str = Field(..., min_length=1)
    temperature: float = Field(0.7, ge=0.0, le=2.0)

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    openai_api_key: str = ""
    groq_api_key: str = ""
    gemini_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    request_timeout: int = 30

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()

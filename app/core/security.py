from app.core.config import get_settings


def require_openai_key() -> str:
    key = get_settings().openai_api_key
    if not key or not key.strip():
        raise ValueError("OPENAI_API_KEY is not set")
    return key


def require_groq_key() -> str:
    key = get_settings().groq_api_key
    if not key or not key.strip():
        raise ValueError("GROQ_API_KEY is not set")
    return key


def require_gemini_key() -> str:
    key = get_settings().gemini_api_key
    if not key or not key.strip():
        raise ValueError("GEMINI_API_KEY is not set")
    return key

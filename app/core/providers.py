PROVIDERS = {
    "openai": {
        "max_tokens": 128000,
        "reasoning": "high",
        "speed": "medium",
        "reasoning_weight": 1.0,
    },
    "groq": {
        "max_tokens": 32000,
        "reasoning": "medium",
        "speed": "ultra_fast",
        "reasoning_weight": 0.6,
    },
    "gemini": {
        "max_tokens": 1000000,
        "reasoning": "high",
        "speed": "medium",
        "reasoning_weight": 1.0,
    },
    "ollama": {
        "max_tokens": 8000,
        "reasoning": "low",
        "speed": "local",
        "reasoning_weight": 0.3,
    },
}

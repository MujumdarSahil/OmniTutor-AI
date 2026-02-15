# -----------------------------------------------------------------------------
# app/security/rate_guard.py — Max request size, fingerprint helper
# -----------------------------------------------------------------------------

import hashlib

MAX_PROMPT_LENGTH = 20_000


def check_prompt_size(prompt: str) -> None:
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ValueError("prompt exceeds maximum length")


def make_fingerprint(ip: str, user_agent: str, prompt_length: int) -> str:
    raw = f"{ip}|{user_agent}|{prompt_length}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

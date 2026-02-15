# -----------------------------------------------------------------------------
# app/security/analyzer.py — Prompt injection detection (flag only, do not block)
# -----------------------------------------------------------------------------

SUSPICIOUS_PHRASES = [
    "ignore previous instructions",
    "system prompt",
    "bypass",
    "override",
    "act as",
    "jailbreak",
]


def analyze_prompt(prompt: str) -> float:
    lower = prompt.lower().strip()
    risk = 0.0
    for phrase in SUSPICIOUS_PHRASES:
        if phrase in lower:
            risk += 1.0
    return min(risk, 10.0)

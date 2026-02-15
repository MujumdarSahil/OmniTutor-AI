import re


def estimate_tokens(text: str) -> int:
    if not text or not text.strip():
        return 0
    words = len(re.findall(r"\S+", text))
    if words == 0:
        return max(1, len(text) // 4)
    estimated = int(words * 1.3)
    return max(estimated, len(text) // 4)

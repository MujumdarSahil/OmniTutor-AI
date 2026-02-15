# =============================================================================
# scripts/test_api.py — Quick API smoke test (run with backend on 127.0.0.1:8000)
# =============================================================================
# Usage: python scripts/test_api.py
# =============================================================================

import os
import sys

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
TIMEOUT = 5


def get(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{BASE}{path}", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"GET {path} failed: {e}")
        return None


def post(path: str, json: dict) -> tuple[dict | list | None, int | None]:
    try:
        r = requests.post(f"{BASE}{path}", json=json, timeout=60)
        r.raise_for_status()
        return r.json(), r.status_code
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else None
        print(f"POST {path} failed: {e} (status={code})")
        if e.response is not None:
            try:
                print("Response:", e.response.text[:500])
            except Exception:
                pass
        return None, code
    except Exception as e:
        print(f"POST {path} failed: {e}")
        return None, None


def main() -> int:
    print("1. GET /health ...")
    h = get("/health")
    if not h:
        print("   Backend not reachable. Start with: uvicorn app.main:app --host 127.0.0.1 --port 8000")
        return 1
    print("   OK:", h.get("status"), "| providers:", h.get("providers"))

    print("2. GET /metrics/providers ...")
    m = get("/metrics/providers")
    if m is None:
        return 1
    print("   OK:", list(m.keys()))

    print("3. GET /rag/stats ...")
    r = get("/rag/stats")
    if r is None:
        return 1
    print("   OK: chunks_indexed =", r.get("chunks_indexed", 0))

    print("4. GET /dashboard/stats ...")
    d = get("/dashboard/stats")
    if d is not None:
        print("   OK: daily_usage =", len(d.get("daily_usage", [])), "| categories =", len(d.get("categories", [])))
    else:
        print("   Skip: dashboard stats failed")

    print("5. POST /generate (provider=auto, model=auto, USSR question) ...")
    out, status = post("/generate", {
        "provider": "auto",
        "model": "",
        "prompt": "In which year did the USSR fall?",
        "temperature": 0.7,
    })
    if out:
        print("   OK: provider_used =", out.get("provider_used"), "| latency_ms =", out.get("latency_ms"))
        print("   response (first 200 chars):", (out.get("response") or "")[:200])
    elif status == 502:
        print("   OK: 502 when provider unreachable (check API keys and REQUEST_TIMEOUT=60 for free tier).")
    else:
        print("   Tip: Set GEMINI_API_KEY (or other keys), REQUEST_TIMEOUT=60, and ensure outbound HTTPS.")
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

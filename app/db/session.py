import datetime
import sqlite3
from contextlib import contextmanager
from typing import Any

from app.db.models import DB_PATH


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _infer_category(prompt: str) -> str:
    """Infer question category from prompt text (for dashboard)."""
    if not prompt or not prompt.strip():
        return "general"
    text = prompt.strip().lower()[:500]
    if any(k in text for k in ("year", "when did", "history", "war", "country", "fall", "century")):
        return "history"
    if any(k in text for k in ("math", "equation", "derivative", "integral", "solve", "calculate")):
        return "math"
    if any(k in text for k in ("physics", "chemistry", "science", "biology", "atom")):
        return "science"
    if any(k in text for k in ("code", "program", "function", "python", "javascript")):
        return "programming"
    return "general"


def insert_log(
    provider: str,
    model: str,
    prompt_length: int,
    latency_ms: float,
    original_provider: str | None = None,
    routing_reason: str | None = None,
    rag_used: bool | None = None,
    risk_score: float | None = None,
    fingerprint: str | None = None,
    adaptive_score_used: float | None = None,
    circuit_triggered: bool | None = None,
    prompt_preview: str | None = None,
    category: str | None = None,
) -> None:
    with get_db_connection() as conn:
        cursor = conn.execute("PRAGMA table_info(logs)")
        columns = {row[1] for row in cursor.fetchall()}
        has_preview = "prompt_preview" in columns and "category" in columns
        has_extras = (
            "rag_used" in columns
            and "risk_score" in columns
            and "fingerprint" in columns
            and "adaptive_score_used" in columns
            and "circuit_triggered" in columns
        )
        ts = datetime.datetime.utcnow().isoformat()
        base = (provider, model, prompt_length, latency_ms, ts, original_provider, routing_reason)
        rag_val = 1 if rag_used else 0 if rag_used is False else None
        circuit_val = 1 if circuit_triggered else 0 if circuit_triggered is False else None
        if has_extras and has_preview:
            conn.execute(
                """INSERT INTO logs (
                    provider, model, prompt_length, latency_ms, timestamp,
                    original_provider, routing_reason, rag_used, risk_score, fingerprint,
                    adaptive_score_used, circuit_triggered, prompt_preview, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*base, rag_val, risk_score, fingerprint, adaptive_score_used, circuit_val,
                 (prompt_preview or "")[:300], category or "general"),
            )
        elif has_extras:
            conn.execute(
                """INSERT INTO logs (
                    provider, model, prompt_length, latency_ms, timestamp,
                    original_provider, routing_reason, rag_used, risk_score, fingerprint,
                    adaptive_score_used, circuit_triggered
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*base, rag_val, risk_score, fingerprint, adaptive_score_used, circuit_val),
            )
        elif "rag_used" in columns and "risk_score" in columns and "fingerprint" in columns:
            conn.execute(
                """INSERT INTO logs (
                    provider, model, prompt_length, latency_ms, timestamp,
                    original_provider, routing_reason, rag_used, risk_score, fingerprint
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*base, rag_val, risk_score, fingerprint),
            )
        else:
            conn.execute(
                """INSERT INTO logs (
                    provider, model, prompt_length, latency_ms, timestamp,
                    original_provider, routing_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                base,
            )


def get_last_logs(limit: int = 20) -> list[dict[str, Any]]:
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_dashboard_stats() -> dict[str, Any]:
    """Daily usage (last 30 days) and question categories for dashboard."""
    with get_db_connection() as conn:
        conn.row_factory = sqlite3.Row
        # Daily usage: date -> count
        cursor = conn.execute(
            """SELECT date(timestamp) AS day, COUNT(*) AS cnt
               FROM logs WHERE timestamp >= date('now', '-30 days')
               GROUP BY date(timestamp) ORDER BY day"""
        )
        daily = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]
        # Categories (use category column if present, else infer from prompt_preview)
        cursor = conn.execute("PRAGMA table_info(logs)")
        columns = {row[1] for row in cursor.fetchall()}
        if "category" in columns:
            cursor = conn.execute(
                """SELECT category AS name, COUNT(*) AS count FROM logs
                   WHERE category IS NOT NULL AND category != ''
                   GROUP BY category ORDER BY count DESC"""
            )
            categories = [{"name": row[0], "count": row[1]} for row in cursor.fetchall()]
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM logs")
            total = cursor.fetchone()[0]
            categories = [{"name": "general", "count": total}] if total else []
        return {"daily_usage": daily, "categories": categories}

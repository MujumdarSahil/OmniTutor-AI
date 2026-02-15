import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "llm_logs.db"


def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                prompt_length INTEGER NOT NULL,
                latency_ms REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        conn.commit()
        cursor = conn.execute("PRAGMA table_info(logs)")
        columns = {row[1] for row in cursor.fetchall()}
        if "original_provider" not in columns:
            conn.execute("ALTER TABLE logs ADD COLUMN original_provider TEXT")
            conn.commit()
        if "routing_reason" not in columns:
            conn.execute("ALTER TABLE logs ADD COLUMN routing_reason TEXT")
            conn.commit()
        if "rag_used" not in columns:
            conn.execute("ALTER TABLE logs ADD COLUMN rag_used INTEGER")
            conn.commit()
        if "risk_score" not in columns:
            conn.execute("ALTER TABLE logs ADD COLUMN risk_score REAL")
            conn.commit()
        if "fingerprint" not in columns:
            conn.execute("ALTER TABLE logs ADD COLUMN fingerprint TEXT")
            conn.commit()
        if "adaptive_score_used" not in columns:
            conn.execute("ALTER TABLE logs ADD COLUMN adaptive_score_used REAL")
            conn.commit()
        if "circuit_triggered" not in columns:
            conn.execute("ALTER TABLE logs ADD COLUMN circuit_triggered INTEGER")
            conn.commit()
        if "prompt_preview" not in columns:
            conn.execute("ALTER TABLE logs ADD COLUMN prompt_preview TEXT")
            conn.commit()
        if "category" not in columns:
            conn.execute("ALTER TABLE logs ADD COLUMN category TEXT")
            conn.commit()

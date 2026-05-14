"""
database.py — обёртка над SQLite.
Одна таблица: records(id, ts, happiness, sadness, anger, stress, energy, calm, source)
"""

import sqlite3
import threading
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "emotions.db"

EMOTIONS = ["Happiness", "Sadness", "Anger", "Stress", "Energy", "Calm"]

_lock = threading.Lock()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    cols = ", ".join(f"{e.lower()} INTEGER NOT NULL DEFAULT 5" for e in EMOTIONS)
    with _lock, get_connection() as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS records (
                id        INTEGER PRIMARY KEY,
                ts        INTEGER NOT NULL,
                {cols},
                source    TEXT NOT NULL DEFAULT 'unknown',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.commit()


def insert_records(records: list[dict], source: str = "unknown") -> tuple[int, int]:
    inserted = 0
    skipped  = 0

    with _lock, get_connection() as conn:
        for rec in records:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO records
                        (id, ts, happiness, sadness, anger, stress, energy, calm, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rec["id"],
                    rec["ts"],
                    rec.get("Happiness", 5),
                    rec.get("Sadness",   5),
                    rec.get("Anger",     5),
                    rec.get("Stress",    5),
                    rec.get("Energy",    5),
                    rec.get("Calm",      5),
                    source,
                ))
                if conn.execute("SELECT changes()").fetchone()[0]:
                    inserted += 1
                else:
                    skipped += 1
            except (KeyError, sqlite3.Error) as e:
                print(f"[DB] Ошибка при вставке записи {rec}: {e}")
                skipped += 1
        conn.commit()

    return inserted, skipped


def fetch_all() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM records ORDER BY ts DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def fetch_stats() -> dict:
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        if total == 0:
            return {"total": 0, "sources": {}, "avg": {}}

        sources = dict(conn.execute(
            "SELECT source, COUNT(*) FROM records GROUP BY source"
        ).fetchall())

        avg_row = conn.execute(f"""
            SELECT {', '.join(f'ROUND(AVG({e.lower()}), 2)' for e in EMOTIONS)}
            FROM records
        """).fetchone()
        avg = {e: avg_row[i] for i, e in enumerate(EMOTIONS)}

    return {"total": total, "sources": sources, "avg": avg}


def ts_to_str(ts: int) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        return str(ts)
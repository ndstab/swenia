"""
SQLite seen-state. Each item is recorded by its content id (sha1 of URL) the
first time it appears in a digest, so it never shows up twice. The digest shows
everything unseen since the user last opened the app.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config as cfg
from .models import Item

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    id          TEXT PRIMARY KEY,
    url         TEXT,
    title       TEXT,
    first_seen  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


@contextmanager
def _conn():
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(cfg.DB_PATH)
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def filter_unseen(items: list[Item]) -> tuple[list[Item], int]:
    """Return (items not previously seen, count_skipped)."""
    with _conn() as conn:
        known = {row[0] for row in conn.execute("SELECT id FROM seen")}
    fresh = [it for it in items if it.id not in known]
    return fresh, len(items) - len(fresh)


def mark_seen(items: list[Item]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.executemany(
            "INSERT OR IGNORE INTO seen (id, url, title, first_seen) VALUES (?,?,?,?)",
            [(it.id, it.url, it.title, now) for it in items],
        )


def get_last_open() -> str | None:
    with _conn() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key='last_open'").fetchone()
    return row[0] if row else None


def set_last_open() -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_open', ?)",
                     (now,))


def seen_count() -> int:
    with _conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM seen").fetchone()[0]

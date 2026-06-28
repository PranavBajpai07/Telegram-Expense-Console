"""SQLite storage helpers for the local expense tracker."""

from __future__ import annotations

from contextlib import closing
import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).with_name("expenses.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS txns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    note TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL CHECK (type IN ('expense', 'income')),
    chat_id TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_txns_month_type ON txns (date, type);
CREATE INDEX IF NOT EXISTS idx_txns_chat_id ON txns (chat_id, id);
"""


def db_path(path: str | Path | None = None) -> Path:
    return Path(path or os.environ.get("EXPENSE_DB_PATH") or DEFAULT_DB_PATH)


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: str | Path | None = None) -> None:
    with closing(connect(path)) as conn, conn:
        conn.executescript(SCHEMA)


def add(entry: dict[str, Any], chat_id: int | str, path: str | Path | None = None) -> dict[str, Any]:
    init_db(path)
    txn_date = entry.get("date") or date.today().isoformat()
    created_at = entry.get("created_at") or datetime.now().astimezone().isoformat(timespec="seconds")

    with closing(connect(path)) as conn, conn:
        cursor = conn.execute(
            """
            INSERT INTO txns (date, category, amount, note, type, chat_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                txn_date,
                str(entry["category"]),
                float(entry["amount"]),
                str(entry.get("note", "")),
                str(entry["type"]),
                str(chat_id),
                created_at,
            ),
        )
        row_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM txns WHERE id = ?", (row_id,)).fetchone()
    return _row_to_dict(row)


def undo_last(chat_id: int | str, path: str | Path | None = None) -> dict[str, Any] | None:
    init_db(path)
    with closing(connect(path)) as conn, conn:
        row = conn.execute(
            "SELECT * FROM txns WHERE chat_id = ? ORDER BY id DESC LIMIT 1",
            (str(chat_id),),
        ).fetchone()
        if row is None:
            return None
        conn.execute("DELETE FROM txns WHERE id = ?", (row["id"],))
    return _row_to_dict(row)


def all_rows(path: str | Path | None = None) -> list[dict[str, Any]]:
    init_db(path)
    with closing(connect(path)) as conn, conn:
        rows = conn.execute("SELECT * FROM txns ORDER BY date ASC, id ASC").fetchall()
    return [_row_to_dict(row) for row in rows]


def month_total(month: str, path: str | Path | None = None) -> float:
    """Return expense total for a month string like YYYY-MM."""
    init_db(path)
    with closing(connect(path)) as conn, conn:
        total = conn.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM txns
            WHERE substr(date, 1, 7) = ? AND type = 'expense'
            """,
            (month,),
        ).fetchone()[0]
    return float(total or 0)


def category_totals(month: str, path: str | Path | None = None) -> dict[str, float]:
    init_db(path)
    with closing(connect(path)) as conn, conn:
        rows = conn.execute(
            """
            SELECT category, COALESCE(SUM(amount), 0) AS total
            FROM txns
            WHERE substr(date, 1, 7) = ? AND type = 'expense'
            GROUP BY category
            ORDER BY total DESC
            """,
            (month,),
        ).fetchall()
    return {row["category"]: float(row["total"] or 0) for row in rows}


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "date": row["date"],
        "category": row["category"],
        "amount": row["amount"],
        "note": row["note"],
        "type": row["type"],
        "chat_id": row["chat_id"],
        "created_at": row["created_at"],
    }

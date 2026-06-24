"""SQLite run ledger — Phase 6.

Stores execution audit logs and ensures idempotency for both
run triggers and output deliveries.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _get_db_path() -> Path:
    """Return the absolute path to the SQLite DB."""
    # Place db in data/ pulse_ledger.db
    data_dir = Path(__file__).resolve().parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "pulse_ledger.db"


def init_db() -> None:
    """Initialize the SQLite ledger database schemas."""
    db_path = _get_db_path()
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                product TEXT NOT NULL,
                iso_week TEXT NOT NULL,
                status TEXT NOT NULL,
                review_count INTEGER DEFAULT 0,
                window_weeks INTEGER DEFAULT 0,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                error_message TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS deliveries (
                run_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                external_id TEXT,
                url TEXT,
                idempotency_key TEXT,
                delivered_at TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)
        # Ensure only one completed run per (product, iso_week)
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_runs_completed 
            ON runs (product, iso_week) 
            WHERE status = 'completed'
        """)


def start_run(product: str, iso_week: str, window_weeks: int) -> str:
    """Record the start of a new pulse run.

    Returns:
        Generated run_id (UUID string).
    """
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    with sqlite3.connect(_get_db_path()) as conn:
        conn.execute(
            """
            INSERT INTO runs (run_id, product, iso_week, status, window_weeks, started_at)
            VALUES (?, ?, ?, 'pending', ?, ?)
            """,
            (run_id, product, iso_week, window_weeks, now)
        )
    return run_id


def complete_run(run_id: str, review_count: int) -> None:
    """Mark a run as successfully completed."""
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_get_db_path()) as conn:
        conn.execute(
            """
            UPDATE runs 
            SET status = 'completed', review_count = ?, completed_at = ?
            WHERE run_id = ?
            """,
            (review_count, now, run_id)
        )


def fail_run(run_id: str, error_message: str) -> None:
    """Mark a run as failed with an error message."""
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_get_db_path()) as conn:
        conn.execute(
            """
            UPDATE runs 
            SET status = 'failed', error_message = ?, completed_at = ?
            WHERE run_id = ?
            """,
            (error_message, now, run_id)
        )


def check_run_completed(product: str, iso_week: str) -> dict[str, Any] | None:
    """Check if a successful run already exists for this product and week.
    
    Returns:
        Run dictionary if completed, else None.
    """
    with sqlite3.connect(_get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT * FROM runs 
            WHERE product = ? AND iso_week = ? AND status = 'completed'
            """,
            (product, iso_week)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def record_delivery(
    run_id: str,
    channel: str,
    external_id: str | None = None,
    url: str | None = None,
    idempotency_key: str | None = None
) -> None:
    """Record a successful delivery (e.g., Google Doc append or Gmail draft)."""
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(_get_db_path()) as conn:
        conn.execute(
            """
            INSERT INTO deliveries (run_id, channel, external_id, url, idempotency_key, delivered_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, channel, external_id, url, idempotency_key, now)
        )


def check_delivery_exists(idempotency_key: str) -> dict[str, Any] | None:
    """Check if a delivery was already made using an idempotency key."""
    with sqlite3.connect(_get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT * FROM deliveries 
            WHERE idempotency_key = ?
            """,
            (idempotency_key,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

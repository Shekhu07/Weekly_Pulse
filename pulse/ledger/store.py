"""Run ledger store — Phase 6.

SQLite-backed audit ledger for run tracking and idempotency.
"""

from __future__ import annotations


def init_ledger(db_path: str = "data/ledger.db") -> None:
    """Initialize the ledger database (create tables if needed).

    Raises:
        NotImplementedError: Stub — implemented in Phase 6.
    """
    raise NotImplementedError("Ledger store not yet implemented (Phase 6)")


def check_idempotency(product: str, iso_week: str) -> dict | None:
    """Check if a run has already completed for this product/week.

    Returns:
        Prior run record if completed, or None.

    Raises:
        NotImplementedError: Stub — implemented in Phase 6.
    """
    raise NotImplementedError("Ledger store not yet implemented (Phase 6)")


def record_run(run_data: dict) -> None:
    """Record a completed (or failed) run in the ledger.

    Raises:
        NotImplementedError: Stub — implemented in Phase 6.
    """
    raise NotImplementedError("Ledger store not yet implemented (Phase 6)")

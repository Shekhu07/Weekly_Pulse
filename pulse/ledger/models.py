"""Ledger data models — Phase 6.

RunRecord and DeliveryRecord for the SQLite audit ledger.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RunRecord:
    """A single pulse run record in the ledger."""
    run_id: str
    product: str
    iso_week: str
    status: str                # "pending", "completed", "failed"
    review_count: int = 0
    window_weeks: int = 0
    started_at: str = ""
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DeliveryRecord:
    """A delivery event (Doc or email) linked to a run."""
    run_id: str
    channel: str               # "google_doc" | "gmail"
    external_id: str           # heading_id, message_id, draft_id
    url: str = ""
    idempotency_key: Optional[str] = None

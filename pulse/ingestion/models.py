"""Core data models for the pulse pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Ingestion models
# ---------------------------------------------------------------------------

@dataclass
class RawReview:
    """Raw review as scraped from Google Play Store.

    Stored in reviews_raw.json cache. Contains the full scrape payload
    before any quality filtering.
    """
    text: str
    rating: int               # 1–5 stars
    published_at: str          # ISO datetime UTC


@dataclass
class Review:
    """Normalized, quality-filtered review ready for the analysis pipeline.

    Stored in reviews_normalized.json cache. Only text and rating are
    kept — all other fields (reviewId, userName, etc.) are stripped
    during normalization.
    """
    text: str                  # Review body passing quality filters
    rating: int                # 1–5 stars


# ---------------------------------------------------------------------------
# Run context
# ---------------------------------------------------------------------------

@dataclass
class RunContext:
    """Parameters for a single pulse run.

    Created by the CLI and threaded through ingestion, pipeline,
    rendering, and delivery.
    """
    product: str               # Product slug, e.g. "groww"
    iso_week: str              # ISO 8601 week, e.g. "2026-W23"
    window_weeks: int          # Rolling review window (8–12)
    dry_run: bool = False      # Skip MCP writes if True
    email_mode: str = "draft"  # "draft" | "send"


# ---------------------------------------------------------------------------
# Pipeline output models
# ---------------------------------------------------------------------------

@dataclass
class ActionIdea:
    """A single action recommendation from the LLM summarizer."""
    title: str
    detail: str


@dataclass
class Theme:
    """A clustered, summarized theme with validated quotes."""
    theme_name: str
    summary: str
    quotes: list[str] = field(default_factory=list)        # Validated only
    action_ideas: list[ActionIdea] = field(default_factory=list)
    cluster_size: int = 0
    avg_rating: float = 0.0


@dataclass
class PulseReport:
    """Complete analysis output — input to renderers."""
    product: str
    iso_week: str
    window_weeks: int
    review_count: int
    themes: list[Theme] = field(default_factory=list)
    generated_at: str = ""     # ISO datetime


# ---------------------------------------------------------------------------
# Delivery models
# ---------------------------------------------------------------------------

@dataclass
class DocSection:
    """Structured content ready for Google Docs MCP append."""
    anchor: str                # e.g. "groww-2026-W23"
    heading_text: str          # e.g. "Groww — Weekly Review Pulse — 2026-W23"
    blocks: list[dict] = field(default_factory=list)  # Structured content blocks


@dataclass
class EmailTeaser:
    """Short notification email content for Gmail MCP."""
    subject: str
    html_body: str
    text_body: str
    recipients: list[str] = field(default_factory=list)
    idempotency_key: str = ""  # e.g. "groww-2026-W23-email"

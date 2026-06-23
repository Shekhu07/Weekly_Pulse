"""PII scrubber — Phase 2a.

Redacts personally identifiable information from review text
before embedding, LLM processing, and publishing.
"""

from __future__ import annotations

from pulse.ingestion.models import Review


def scrub_reviews(reviews: list[Review]) -> list[Review]:
    """Scrub PII from review texts.

    Patterns redacted:
        - Email addresses → [EMAIL]
        - Phone numbers (IN formats) → [PHONE]
        - Long numeric sequences (PAN/Aadhaar-like) → [ID]
        - URLs with tokens → path/query redacted
        - Financial amounts → kept (useful signal)

    Args:
        reviews: Normalized reviews.

    Returns:
        New list of Reviews with scrubbed text.

    Raises:
        NotImplementedError: Stub — implemented in Phase 2.
    """
    raise NotImplementedError("PII scrubber not yet implemented (Phase 2)")

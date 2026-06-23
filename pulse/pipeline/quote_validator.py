"""Quote validator — Phase 2e.

Validates that LLM-generated quotes are real substrings of
source review texts. Prevents hallucinated quotes from
reaching stakeholders.
"""

from __future__ import annotations

from pulse.ingestion.models import Review, Theme


def validate_quotes(theme: Theme, cluster_reviews: list[Review], all_reviews: list[Review]) -> Theme:
    """Validate quotes in a Theme against source review texts.

    Validation rules:
        - Case-insensitive substring match in cluster reviews (primary).
        - Fallback: match against full scrubbed corpus.
        - Accept ellipsis truncation (... / …) as prefix match.
        - Drop invalid quotes; log failures.

    Args:
        theme: Theme with LLM-generated quotes.
        cluster_reviews: Reviews in the theme's cluster.
        all_reviews: Full scrubbed review corpus (fallback).

    Returns:
        Theme with only validated quotes. May have empty quotes list.

    Raises:
        NotImplementedError: Stub — implemented in Phase 2.
    """
    raise NotImplementedError("Quote validator not yet implemented (Phase 2)")

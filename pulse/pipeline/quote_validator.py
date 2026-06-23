"""Quote validator — Phase 2e.

Validates that LLM-generated quotes are real substrings of source
review texts. Prevents hallucinated quotes from reaching stakeholders.

Ellipsis rule: accept `...` / `…` truncation ONLY if the prefix
before the ellipsis is >= 15 characters. Groww reviews commonly use
trailing `....` as casual punctuation — a short prefix match would
cause false-positives.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from pulse.ingestion.models import Review, Theme

logger = logging.getLogger(__name__)

_ELLIPSIS_CHARS = ("...", "…")
_ELLIPSIS_MIN_PREFIX_LEN = 15  # characters before ellipsis required for truncation match


# ---------------------------------------------------------------------------
# Text normalization helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalize whitespace and punctuation for matching."""
    # Normalize unicode (e.g. different apostrophes → ')
    text = unicodedata.normalize("NFKC", text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Lowercase for case-insensitive match
    return text.lower()


# ---------------------------------------------------------------------------
# Single-quote validation
# ---------------------------------------------------------------------------

def _validate_quote(quote: str, corpus: list[str]) -> bool:
    """Check if quote is a substring of any review in corpus.

    Handles:
    - Case-insensitive full substring match
    - Ellipsis truncation (quote ends with ... / …) with >= 15 char prefix
    """
    norm_quote = _normalize(quote)

    # Check for ellipsis truncation
    for ellipsis in _ELLIPSIS_CHARS:
        if norm_quote.endswith(ellipsis):
            prefix = norm_quote[: -len(ellipsis)].rstrip()
            if len(prefix) >= _ELLIPSIS_MIN_PREFIX_LEN:
                # Accept if prefix is a substring of any review
                return any(prefix in _normalize(rev) for rev in corpus)
            # Prefix too short — fall through to full match attempt
            break

    # Full (or non-ellipsis) substring match
    return any(norm_quote in _normalize(rev) for rev in corpus)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_quotes(
    theme: Theme,
    cluster_reviews: list[Review],
    all_reviews: list[Review],
) -> Theme:
    """Validate quotes in a Theme against source review texts.

    Validation order:
      1. Case-insensitive substring match in cluster reviews (primary)
      2. Fallback: match against full scrubbed corpus

    Quotes failing both checks are dropped and logged.

    Args:
        theme: Theme with LLM-generated quotes.
        cluster_reviews: Reviews in this theme's cluster.
        all_reviews: Full scrubbed review corpus (fallback).

    Returns:
        Theme with only validated quotes. May have empty quotes list.
    """
    cluster_texts = [r.text for r in cluster_reviews]
    all_texts = [r.text for r in all_reviews]

    validated: list[str] = []
    dropped: list[str] = []

    for quote in theme.quotes:
        # Primary: check cluster reviews
        if _validate_quote(quote, cluster_texts):
            validated.append(quote)
            continue
        # Fallback: check full corpus
        if _validate_quote(quote, all_texts):
            validated.append(quote)
            logger.debug(f"Quote validated via corpus fallback: {quote[:60]!r}")
            continue
        # Drop
        dropped.append(quote)
        logger.warning(
            f"Quote dropped (no source match) in theme {theme.theme_name!r}: "
            f"{quote[:80]!r}"
        )

    if dropped:
        logger.info(
            f"Theme {theme.theme_name!r}: "
            f"{len(validated)} quotes kept, {len(dropped)} dropped"
        )

    return Theme(
        theme_name=theme.theme_name,
        summary=theme.summary,
        quotes=validated,
        action_ideas=theme.action_ideas,
        cluster_size=theme.cluster_size,
        avg_rating=theme.avg_rating,
    )

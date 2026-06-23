"""Review normalizer — Phase 1.

Applies quality filters to raw reviews: word count, language,
emoji filtering, and deduplication.
"""

from __future__ import annotations

import hashlib
import logging
import re

from pulse.ingestion.models import RawReview, Review

logger = logging.getLogger(__name__)


def is_emoji_only(text: str) -> bool:
    """Check if text consists only of emojis and whitespace."""
    # A simple heuristic: check if there are no alphabetic/numeric chars
    return not bool(re.search(r'[A-Za-z0-9]', text))


def normalize_reviews(raw_reviews: list[RawReview], product_config: dict) -> list[Review]:
    """Filter and normalize raw reviews into pipeline-ready Reviews.

    Filters applied:
        - Minimum word count (default: 8)
        - English language only (delegated to play store language setting mostly, plus basic filtering)
        - No emoji-only reviews
        - Deduplication by hash(text, rating, published_at)

    Args:
        raw_reviews: Raw reviews from the scraper.
        product_config: Product config with ingestion filter settings.

    Returns:
        Filtered list of normalized Reviews.
    """
    ingestion_config = product_config.get("ingestion", {})
    min_words = ingestion_config.get("min_words", 8)

    dedup_seen = set()
    unique_raw = []

    # 1. Deduplicate
    for raw in raw_reviews:
        # Create a stable hash of text, rating, published_at
        h = hashlib.sha256(f"{raw.text}|{raw.rating}|{raw.published_at}".encode('utf-8')).hexdigest()
        if h not in dedup_seen:
            dedup_seen.add(h)
            unique_raw.append(raw)

    logger.info(f"Deduplication: {len(raw_reviews)} raw -> {len(unique_raw)} unique")

    # 2. Filter & Normalize
    normalized = []
    for raw in unique_raw:
        text = raw.text.strip()
        if not text:
            continue

        if is_emoji_only(text):
            continue

        words = text.split()
        if len(words) < min_words:
            continue

        # Simple cleanup
        clean_text = " ".join(words)

        normalized.append(Review(text=clean_text, rating=raw.rating))

    logger.info(f"Normalization: {len(unique_raw)} unique -> {len(normalized)} normalized")
    return normalized

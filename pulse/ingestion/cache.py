"""Review cache layer — Phase 1.

Caches raw and normalized reviews under data/cache/{product}/{date}/
to avoid re-scraping on retries.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pulse.ingestion.models import RawReview, Review

logger = logging.getLogger(__name__)


def _get_cache_dir(product: str, date_str: str) -> Path:
    from pulse.config import _project_root
    return _project_root() / "data" / "cache" / product / date_str


def save_to_cache(
    product: str,
    raw_reviews: list[RawReview],
    normalized_reviews: list[Review],
    window_weeks: int = 0,
) -> str:
    """Save raw and normalized reviews to the cache directory.

    Creates: data/cache/{product}/{date}/
        - reviews_raw.json
        - reviews_normalized.json
        - manifest.json

    Args:
        product: Product slug.
        raw_reviews: Raw scraped reviews.
        normalized_reviews: Quality-filtered reviews.
        window_weeks: The configured rolling review window.

    Returns:
        Path to the cache directory.
    """
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cache_dir = _get_cache_dir(product, date_str)
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Save raw
    raw_path = cache_dir / "reviews_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump([vars(r) for r in raw_reviews], f, ensure_ascii=False, indent=2)

    # Save normalized
    norm_path = cache_dir / "reviews_normalized.json"
    with open(norm_path, "w", encoding="utf-8") as f:
        json.dump([vars(r) for r in normalized_reviews], f, ensure_ascii=False, indent=2)

    # Save manifest
    manifest_path = cache_dir / "manifest.json"
    manifest = {
        "product": product,
        "fetch_date": date_str,
        "window_weeks": window_weeks,
        "raw_count": len(raw_reviews),
        "normalized_count": len(normalized_reviews),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(f"Saved cache to {cache_dir}")
    return str(cache_dir)


def load_from_cache(product: str, date_str: str | None = None) -> tuple[list[RawReview], list[Review]] | None:
    """Load cached reviews if available.

    Args:
        product: Product slug.
        date_str: Specific date to load (YYYY-MM-DD). If None, uses today.

    Returns:
        Tuple of (raw_reviews, normalized_reviews) or None if no cache.
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cache_dir = _get_cache_dir(product, date_str)
    if not cache_dir.exists():
        return None

    try:
        with open(cache_dir / "reviews_raw.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            raw_reviews = [RawReview(**d) for d in raw_data]

        with open(cache_dir / "reviews_normalized.json", "r", encoding="utf-8") as f:
            norm_data = json.load(f)
            normalized_reviews = [Review(**d) for d in norm_data]

        logger.info(f"Loaded cache from {cache_dir}")
        return raw_reviews, normalized_reviews
    except Exception as e:
        logger.warning(f"Failed to load cache from {cache_dir}: {e}")
        return None

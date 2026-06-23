"""Ingestion package — Play Store scraping, normalization, and caching."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pulse.ingestion.cache import load_from_cache, save_to_cache
from pulse.ingestion.models import RawReview, Review, RunContext
from pulse.ingestion.normalizer import normalize_reviews
from pulse.ingestion.play_store import fetch_reviews

logger = logging.getLogger(__name__)

def fetch_and_cache_reviews(product_config: dict, run_context: RunContext) -> list[Review]:
    """High-level entry point for Phase 1.
    
    1. Check cache for today.
    2. If found, return cached normalized reviews.
    3. Else, fetch from Play Store.
    4. Normalize.
    5. Save to cache.
    6. Return normalized reviews.
    """
    product = run_context.product
    
    # Try cache
    cached = load_from_cache(product)
    if cached is not None:
        raw_reviews, normalized_reviews = cached
        logger.info(f"Using cached reviews for {product} (raw: {len(raw_reviews)}, normalized: {len(normalized_reviews)})")
        return normalized_reviews
        
    # Fetch
    logger.info(f"Fetching fresh reviews for {product}...")
    raw_reviews = fetch_reviews(product_config, run_context)
    if not raw_reviews:
        raise ValueError(f"No reviews returned from Play Store for {product}")
        
    # Normalize
    normalized_reviews = normalize_reviews(raw_reviews, product_config)
    
    # Save
    save_to_cache(product, raw_reviews, normalized_reviews, window_weeks=run_context.window_weeks)
    
    return normalized_reviews

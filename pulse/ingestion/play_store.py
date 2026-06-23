"""Play Store review scraper — Phase 1.

Fetches public reviews for a product from Google Play Store
using the google-play-scraper library.
"""

import logging
import time
from datetime import datetime, timedelta, timezone

from google_play_scraper import Sort, reviews

from pulse.ingestion.models import RawReview, RunContext

logger = logging.getLogger(__name__)


def fetch_reviews(product_config: dict, run_context: RunContext) -> list[RawReview]:
    """Fetch Play Store reviews within the configured window.

    Args:
        product_config: Loaded product YAML config.
        run_context: Current run parameters.

    Returns:
        List of raw reviews from the Play Store.

    Raises:
        RuntimeError: If scraping fails after max retries.
        ValueError: If app_id is missing from config.
    """
    app_id = product_config.get("play_store", {}).get("app_id")
    if not app_id:
        raise ValueError("Missing play_store.app_id in product config")

    ingestion_config = product_config.get("ingestion", {})
    max_reviews = ingestion_config.get("max_reviews", 5000)
    window_weeks = run_context.window_weeks
    iso_week = run_context.iso_week

    # Calculate date window (UTC)
    # The end date is the end of the specified ISO week (Sunday 23:59:59).
    end_date_str = f"{iso_week}-7 23:59:59"
    end_date = datetime.strptime(end_date_str, "%G-W%V-%u %H:%M:%S").replace(tzinfo=timezone.utc)
    start_date = end_date - timedelta(weeks=window_weeks)

    logger.info(f"Fetching reviews for {app_id} from {start_date.date()} to {end_date.date()}")

    collected_raw_reviews: list[RawReview] = []
    continuation_token = None
    retries = 0
    max_retries = 3

    while len(collected_raw_reviews) < max_reviews:
        try:
            result, continuation_token = reviews(
                app_id,
                lang='en',
                country='in',
                sort=Sort.NEWEST,
                count=200,
                continuation_token=continuation_token
            )
        except Exception as e:
            if retries < max_retries:
                backoff = 2 ** (retries + 1)
                logger.warning(f"Scrape failed: {e}. Retrying in {backoff}s...")
                time.sleep(backoff)
                retries += 1
                continue
            else:
                logger.error("Max retries reached. Aborting run.")
                raise RuntimeError("Failed to fetch reviews after retries") from e

        retries = 0

        if not result:
            break

        out_of_window = False
        for rv in result:
            # rv['at'] is naive, usually local time of the review, assume UTC for simplicity
            rv_date = rv['at'].replace(tzinfo=timezone.utc)

            if rv_date > end_date:
                continue

            if rv_date < start_date:
                out_of_window = True
                break

            collected_raw_reviews.append(
                RawReview(
                    text=rv.get('content', '') or '',
                    rating=rv.get('score', 0),
                    published_at=rv_date.isoformat()
                )
            )

        if out_of_window or not continuation_token:
            break

    # Truncate to max_reviews in case of a viral event
    collected_raw_reviews = collected_raw_reviews[:max_reviews]

    if not collected_raw_reviews:
        logger.warning(f"No reviews returned from Play Store in the given window for {app_id}.")

    return collected_raw_reviews

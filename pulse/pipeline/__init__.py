"""Analysis pipeline package — Phase 2.

Entry point: analyze(reviews, pipeline_config) -> PulseReport

Full flow:
  1. Scrub (language filter + PII redaction)
  2. Embed (OpenAI text-embedding-3-small, with disk cache)
  3. Cluster (UMAP + HDBSCAN, ranked by score = size × (6 − avg_rating))
  4. Summarize (Groq, rating-stratified sampling, sequential)
  5. Validate quotes (substring match, ≥15 char ellipsis rule)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pulse.ingestion.models import PulseReport, Review, RunContext
from pulse.pipeline.clustering import cluster_reviews
from pulse.pipeline.embeddings import embed_reviews
from pulse.pipeline.quote_validator import validate_quotes
from pulse.pipeline.scrubber import scrub_reviews
from pulse.pipeline.summarizer import summarize_all_clusters

logger = logging.getLogger(__name__)


def analyze(
    reviews: list[Review],
    run_context: RunContext,
    pipeline_config: dict,
) -> PulseReport:
    """Run the full Phase 2 analysis pipeline.

    Args:
        reviews: Normalized reviews from Phase 1 cache.
        run_context: Current run parameters (product, iso_week, …).
        pipeline_config: Pipeline YAML config.

    Returns:
        PulseReport with validated themes, quotes, and action ideas.

    Raises:
        ValueError: If review count < 20 (ML floor).
    """
    logger.info(
        f"Pipeline starting: {len(reviews)} reviews "
        f"| product={run_context.product} | week={run_context.iso_week}"
    )

    # 2a — Scrub
    scrubbed = scrub_reviews(reviews)
    logger.info(f"After scrubbing: {len(scrubbed)} reviews")

    if len(scrubbed) < 20:
        raise ValueError(
            f"ML floor: only {len(scrubbed)} reviews after scrubbing (need >= 20)."
        )

    # 2b — Embed
    embeddings = embed_reviews(scrubbed, pipeline_config)

    # 2c — Cluster
    clusters = cluster_reviews(embeddings, scrubbed, pipeline_config)
    if not clusters:
        raise RuntimeError("Clustering produced no clusters. Aborting pipeline.")

    # 2d — Summarize
    themes = summarize_all_clusters(clusters, scrubbed, pipeline_config)

    # 2e — Validate quotes
    validated_themes = []
    for theme, cluster in zip(themes, clusters):
        cluster_reviews_list = [scrubbed[i] for i in cluster["indices"]]
        validated = validate_quotes(theme, cluster_reviews_list, scrubbed)
        validated_themes.append(validated)

    # Calculate distributions for dashboard
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    sentiment_distribution = {"Positive": 0, "Neutral": 0, "Negative": 0}
    
    for r in scrubbed:
        rating_distribution[r.rating] += 1
        if r.rating >= 4:
            sentiment_distribution["Positive"] += 1
        elif r.rating == 3:
            sentiment_distribution["Neutral"] += 1
        else:
            sentiment_distribution["Negative"] += 1

    report = PulseReport(
        product=run_context.product,
        iso_week=run_context.iso_week,
        window_weeks=run_context.window_weeks,
        review_count=len(scrubbed),
        rating_distribution=rating_distribution,
        sentiment_distribution=sentiment_distribution,
        themes=validated_themes,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(
        f"Pipeline complete: {len(validated_themes)} themes, "
        f"{sum(len(t.quotes) for t in validated_themes)} validated quotes"
    )
    return report

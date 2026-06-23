"""Clustering — Phase 2c.

UMAP dimensionality reduction + HDBSCAN density-based clustering.
Cluster ranking: score = size × (6 − avg_rating).

Fallbacks:
  - All noise: lower min_cluster_size once, then abort or single LLM pass
  - Dominant cluster > 60%: mandatory rating split (1-2★ vs 4-5★)
  - Many micro-clusters: take top max_themes by score only
"""

from __future__ import annotations

import logging
import random
from typing import Any

import numpy as np

from pulse.ingestion.models import Review

logger = logging.getLogger(__name__)


def _build_clusters(
    embeddings: np.ndarray,
    umap_params: dict,
    hdbscan_params: dict,
) -> np.ndarray:
    """Run UMAP + HDBSCAN and return cluster labels array."""
    import umap
    import hdbscan as hdbscan_lib

    reducer = umap.UMAP(
        n_neighbors=umap_params.get("n_neighbors", 15),
        n_components=umap_params.get("n_components", 5),
        metric=umap_params.get("metric", "cosine"),
        random_state=umap_params.get("random_state", 42),
        low_memory=True,
    )
    reduced = reducer.fit_transform(embeddings)
    logger.info(f"UMAP: {embeddings.shape} → {reduced.shape}")

    clusterer = hdbscan_lib.HDBSCAN(
        min_cluster_size=hdbscan_params.get("min_cluster_size", 5),
        min_samples=hdbscan_params.get("min_samples", 3),
    )
    labels = clusterer.fit_predict(reduced)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise_count = int((labels == -1).sum())
    logger.info(f"HDBSCAN: {n_clusters} clusters, {noise_count} noise points")
    return labels


def _rank_clusters(
    labels: np.ndarray,
    reviews: list[Review],
) -> list[dict[str, Any]]:
    """Build ranked cluster dicts (excluding noise label -1)."""
    from collections import defaultdict
    cluster_indices: dict[int, list[int]] = defaultdict(list)
    for idx, lbl in enumerate(labels):
        if lbl != -1:
            cluster_indices[lbl].append(idx)

    clusters = []
    for lbl, indices in cluster_indices.items():
        ratings = [reviews[i].rating for i in indices]
        avg_rating = sum(ratings) / len(ratings)
        score = len(indices) * (6 - avg_rating)
        clusters.append({
            "label": lbl,
            "indices": indices,
            "size": len(indices),
            "avg_rating": round(avg_rating, 2),
            "score": round(score, 2),
        })

    clusters.sort(key=lambda c: c["score"], reverse=True)
    return clusters


def _rating_split(
    cluster: dict[str, Any],
    reviews: list[Review],
) -> list[dict[str, Any]]:
    """Split a dominant cluster into low-star and high-star sub-clusters."""
    low_indices = [i for i in cluster["indices"] if reviews[i].rating <= 2]
    high_indices = [i for i in cluster["indices"] if reviews[i].rating >= 4]
    mid_indices = [i for i in cluster["indices"] if reviews[i].rating == 3]

    sub_clusters = []
    for label_suffix, indices in [("low", low_indices + mid_indices), ("high", high_indices)]:
        if not indices:
            continue
        ratings = [reviews[i].rating for i in indices]
        avg_rating = sum(ratings) / len(ratings)
        score = len(indices) * (6 - avg_rating)
        sub_clusters.append({
            "label": f"{cluster['label']}_{label_suffix}",
            "indices": indices,
            "size": len(indices),
            "avg_rating": round(avg_rating, 2),
            "score": round(score, 2),
        })

    sub_clusters.sort(key=lambda c: c["score"], reverse=True)
    return sub_clusters


def cluster_reviews(
    embeddings: np.ndarray,
    reviews: list[Review],
    pipeline_config: dict,
) -> list[dict[str, Any]]:
    """Cluster embedded reviews and return ranked top-N clusters.

    Applies UMAP + HDBSCAN, ranks by score = size × (6 − avg_rating),
    and handles dominant-cluster and all-noise fallbacks.

    Args:
        embeddings: numpy.ndarray shape (n_reviews, dim).
        reviews: Corresponding Review objects in same order.
        pipeline_config: Pipeline config with clustering params.

    Returns:
        List of cluster dicts sorted by score (descending), capped at max_themes.
        Each dict: label, indices, size, avg_rating, score.
    """
    cluster_cfg = pipeline_config.get("clustering", {})
    umap_params = cluster_cfg.get("umap", {})
    hdbscan_params = cluster_cfg.get("hdbscan", {})
    max_themes = pipeline_config.get("summarization", {}).get("max_themes", 5)
    n_reviews = len(reviews)

    labels = _build_clusters(embeddings, umap_params, hdbscan_params)

    # Fallback: all noise → retry with smaller min_cluster_size
    all_noise = all(lbl == -1 for lbl in labels)
    if all_noise:
        reduced_min = max(2, hdbscan_params.get("min_cluster_size", 5) - 2)
        logger.warning(
            f"All reviews are noise — retrying with min_cluster_size={reduced_min}"
        )
        labels = _build_clusters(
            embeddings,
            umap_params,
            {**hdbscan_params, "min_cluster_size": reduced_min},
        )
        if all(lbl == -1 for lbl in labels):
            # Last resort: treat everything as one cluster
            logger.warning("Still all noise after retry — treating all reviews as single cluster")
            labels = np.zeros(n_reviews, dtype=int)

    clusters = _rank_clusters(labels, reviews)

    if not clusters:
        logger.error("No clusters produced. Aborting.")
        return []

    # Fallback: dominant cluster > 60% — mandatory rating split
    top_fraction = clusters[0]["size"] / n_reviews
    if top_fraction > 0.60:
        logger.info(
            f"Dominant cluster ({clusters[0]['size']}/{n_reviews} = {top_fraction:.1%}) "
            f"> 60% — applying mandatory rating split"
        )
        split = _rating_split(clusters[0], reviews)
        clusters = split + clusters[1:]
        clusters.sort(key=lambda c: c["score"], reverse=True)

    # Cap at max_themes
    top_clusters = clusters[:max_themes]

    logger.info(
        f"Clustering complete: returning {len(top_clusters)} clusters "
        f"(scores: {[c['score'] for c in top_clusters]})"
    )
    return top_clusters

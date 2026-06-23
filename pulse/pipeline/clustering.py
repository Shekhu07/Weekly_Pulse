"""Clustering — Phase 2c.

UMAP dimensionality reduction + HDBSCAN density-based clustering.
Ranks clusters by score = size × (6 − avg_rating).
"""

from __future__ import annotations


def cluster_reviews(embeddings, reviews: list, pipeline_config: dict) -> list[dict]:
    """Cluster embedded reviews and rank by complaint severity.

    Args:
        embeddings: numpy.ndarray of review embeddings.
        reviews: Corresponding Review objects.
        pipeline_config: Pipeline config with clustering params.

    Returns:
        List of cluster dicts sorted by score, each containing:
            - label: int (cluster ID)
            - indices: list[int] (review indices)
            - size: int
            - avg_rating: float
            - score: float

    Raises:
        NotImplementedError: Stub — implemented in Phase 2.
    """
    raise NotImplementedError("Clustering not yet implemented (Phase 2)")

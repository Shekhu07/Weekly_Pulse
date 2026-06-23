"""Embeddings — Phase 2b.

Generates vector embeddings for scrubbed review texts using
OpenAI text-embedding-3-small.
"""

from __future__ import annotations

from pulse.ingestion.models import Review


def embed_reviews(reviews: list[Review], pipeline_config: dict):
    """Generate embeddings for review texts.

    Args:
        reviews: Scrubbed reviews.
        pipeline_config: Pipeline config with embedding settings.

    Returns:
        numpy.ndarray of shape (n_reviews, embedding_dim).

    Raises:
        NotImplementedError: Stub — implemented in Phase 2.
    """
    raise NotImplementedError("Embeddings not yet implemented (Phase 2)")

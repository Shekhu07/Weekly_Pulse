"""Embeddings — Phase 2b.

Generates vector embeddings for scrubbed review texts using
a local sentence-transformers model (BAAI/bge-small-en-v1.5).
No API key required — model is downloaded once to HuggingFace cache.

Cache: per-review disk cache keyed by sha256(text + rating) at
data/embeddings_cache/ to avoid re-encoding on pipeline retries.

Model: BAAI/bge-small-en-v1.5
  - 384-dim vectors
  - ~80 MB download (one-time)
  - Excellent English embedding quality
  - Fully local, zero API cost
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

import numpy as np

from pulse.ingestion.models import Review

logger = logging.getLogger(__name__)

_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "embeddings_cache"


def _cache_path(key: str) -> Path:
    return _CACHE_DIR / f"{key}.json"


def _review_key(review: Review) -> str:
    return hashlib.sha256(f"{review.text}{review.rating}".encode()).hexdigest()


def _load_cached(key: str) -> list[float] | None:
    path = _cache_path(key)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return None
    return None


def _save_cached(key: str, vector: list[float]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(key).write_text(json.dumps(vector))


def embed_reviews(reviews: list[Review], pipeline_config: dict) -> np.ndarray:
    """Generate embeddings for review texts using a local sentence-transformers model.

    Checks disk cache first per review (sha256 key). Only encodes
    uncached reviews in batches using the configured model.

    Args:
        reviews: Scrubbed, filtered reviews.
        pipeline_config: Pipeline YAML config with embedding settings.

    Returns:
        numpy.ndarray of shape (n_reviews, embedding_dim).

    Raises:
        ValueError: If review count < 20 (ML floor).
    """
    if len(reviews) < 20:
        raise ValueError(
            f"ML floor: only {len(reviews)} reviews — need >= 20 to run embeddings."
        )

    emb_config = pipeline_config.get("embedding", {})
    model_name = emb_config.get("model", "BAAI/bge-small-en-v1.5")
    batch_size = emb_config.get("batch_size", 64)

    keys = [_review_key(r) for r in reviews]
    vectors: dict[str, list[float]] = {}

    # Load from cache
    cache_hits = 0
    to_encode: list[tuple[str, Review]] = []
    for key, review in zip(keys, reviews):
        cached = _load_cached(key)
        if cached is not None:
            vectors[key] = cached
            cache_hits += 1
        else:
            to_encode.append((key, review))

    logger.info(
        f"Embeddings: {len(reviews)} reviews | "
        f"{cache_hits} cache hits, {len(to_encode)} to encode | model={model_name}"
    )

    if to_encode:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading model {model_name!r} (downloads on first use)...")
        model = SentenceTransformer(model_name)

        texts = [r.text for _, r in to_encode]

        logger.info(f"Encoding {len(texts)} reviews in batches of {batch_size}...")
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # bge-small works best with normalized vectors
        )

        for (key, _), vec in zip(to_encode, embeddings):
            vec_list = vec.tolist()
            vectors[key] = vec_list
            _save_cached(key, vec_list)

    # Assemble in original order
    matrix = np.array([vectors[key] for key in keys], dtype=np.float32)
    logger.info(f"Embeddings: matrix shape {matrix.shape}")
    return matrix

"""Embeddings — Phase 2b.

Generates vector embeddings for scrubbed review texts using
a local sentence-transformers model (BAAI/bge-small-en-v1.5).
No API key required — model is downloaded once to HuggingFace cache.

Cache: Batched disk cache stored in a single JSON file at
data/embeddings_cache/cache.json, keyed by sha256(text + rating).
This avoids hundreds of individual file I/O operations per run.

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
_CACHE_FILE = _CACHE_DIR / "cache.json"

# ---------------------------------------------------------------------------
# Singleton model cache — load once, reuse across runs
# ---------------------------------------------------------------------------

_model_instance = None
_model_name_loaded: str | None = None


def _get_model(model_name: str):
    """Get or create a cached SentenceTransformer instance."""
    global _model_instance, _model_name_loaded
    if _model_instance is None or _model_name_loaded != model_name:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading model {model_name!r} (one-time, cached for future runs)...")
        _model_instance = SentenceTransformer(model_name)
        _model_name_loaded = model_name
    return _model_instance


def preload_model(model_name: str = "BAAI/bge-small-en-v1.5") -> None:
    """Pre-load the embedding model at app startup (non-blocking warm-up).

    Call this during server initialization so the first pipeline run
    doesn't pay the cold-load penalty (~10-30s on HF Spaces).
    """
    _get_model(model_name)
    logger.info("Embedding model pre-loaded and ready.")


# ---------------------------------------------------------------------------
# Batched disk cache — single file instead of per-review files
# ---------------------------------------------------------------------------

def _review_key(review: Review) -> str:
    return hashlib.sha256(f"{review.text}{review.rating}".encode()).hexdigest()


def _load_cache() -> dict[str, list[float]]:
    """Load the entire embedding cache from disk (single file)."""
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load embedding cache: {e}")
    return {}


def _save_cache(cache: dict[str, list[float]]) -> None:
    """Save the entire embedding cache to disk (single file)."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, "w") as f:
        json.dump(cache, f)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def embed_reviews(reviews: list[Review], pipeline_config: dict) -> np.ndarray:
    """Generate embeddings for review texts using a local sentence-transformers model.

    Checks batched disk cache first (single file). Only encodes
    uncached reviews using the cached model singleton.

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

    # Load full cache from single file
    cache = _load_cache()

    cache_hits = 0
    to_encode: list[tuple[str, Review]] = []
    for key, review in zip(keys, reviews):
        if key in cache:
            cache_hits += 1
        else:
            to_encode.append((key, review))

    logger.info(
        f"Embeddings: {len(reviews)} reviews | "
        f"{cache_hits} cache hits, {len(to_encode)} to encode | model={model_name}"
    )

    if to_encode:
        model = _get_model(model_name)

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
            cache[key] = vec.tolist()

        # Write back the updated cache once
        _save_cache(cache)

    # Assemble in original order
    matrix = np.array([cache[key] for key in keys], dtype=np.float32)
    logger.info(f"Embeddings: matrix shape {matrix.shape}")
    return matrix

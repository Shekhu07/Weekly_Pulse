"""LLM summarizer — Phase 2d.

Uses Groq llama-3.3-70b-versatile to generate theme names,
summaries, quotes, and action ideas per cluster.
"""

from __future__ import annotations

from pulse.ingestion.models import Review, Theme


def summarize_cluster(
    cluster: dict,
    reviews: list[Review],
    pipeline_config: dict,
) -> Theme:
    """Summarize a single cluster into a Theme using the LLM.

    Args:
        cluster: Cluster dict with indices, size, avg_rating.
        reviews: Full review list (cluster['indices'] used to select samples).
        pipeline_config: Pipeline config with summarization settings.

    Returns:
        Theme with theme_name, summary, quotes, action_ideas.

    Raises:
        NotImplementedError: Stub — implemented in Phase 2.
    """
    raise NotImplementedError("LLM summarizer not yet implemented (Phase 2)")

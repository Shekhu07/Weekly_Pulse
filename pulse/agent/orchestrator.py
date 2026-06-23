"""Orchestrator — Phase 6.

End-to-end run coordinator: ingestion → analysis → rendering → delivery → ledger.
"""

from __future__ import annotations

from pulse.ingestion.models import RunContext


def execute_run(run_context: RunContext, product_config: dict, pipeline_config: dict) -> dict:
    """Execute a full pulse run for a product and ISO week.

    Flow:
        1. Check ledger idempotency
        2. Ingest reviews (scrape or cache)
        3. Run analysis pipeline (scrub → embed → cluster → summarize → validate)
        4. Render outputs (Doc section + email teaser)
        5. Deliver via MCP (Docs + Gmail) — skipped in dry_run
        6. Record run in ledger
        7. Return audit summary

    Args:
        run_context: Run parameters (product, week, mode).
        product_config: Product YAML config.
        pipeline_config: Pipeline YAML config.

    Returns:
        Audit summary dict with run_id, status, delivery IDs.

    Raises:
        NotImplementedError: Stub — implemented in Phase 6.
    """
    raise NotImplementedError("Orchestrator not yet implemented (Phase 6)")

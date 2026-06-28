"""Orchestrator — Phase 6.

End-to-end run coordinator: ingestion → analysis → rendering → delivery → ledger.
"""

from __future__ import annotations

import logging
import json
from pathlib import Path
from dataclasses import asdict

from pulse.agent.mcp_client import append_doc_section, send_email_teaser
from pulse.ingestion.models import RunContext, Review
from pulse.ingestion.play_store import fetch_reviews
from pulse.ledger.db import (
    check_delivery_exists,
    check_run_completed,
    complete_run,
    fail_run,
    init_db,
    record_delivery,
    start_run,
)
from pulse.pipeline import analyze
from pulse.render.doc_section import build_doc_section
from pulse.render.email_teaser import build_email_teaser

logger = logging.getLogger(__name__)


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
    """
    logger.info(f"Starting pulse run for {run_context.product} ({run_context.iso_week})")
    
    # Ensure ledger is initialized
    init_db()

    # 1. Idempotency check
    completed = check_run_completed(run_context.product, run_context.iso_week)
    if completed:
        logger.info(f"Run already completed for {run_context.product} {run_context.iso_week}. Skipping.")
        return {"status": "skipped_already_completed", "run_id": completed["run_id"]}

    run_id = start_run(run_context.product, run_context.iso_week, run_context.window_weeks)
    
    try:
        # 2. Ingest
        logger.info("Phase 1: Ingestion")
        try:
            fetch_reviews(product_config, run_context)
        except NotImplementedError:
            # fetch_reviews is a stub for Phase 1. 
            # Use cached normalized reviews for testing.
            pass
            
        cache_path = Path(f"data/cache/{run_context.product}")
        latest_cache = sorted(cache_path.iterdir(), reverse=True)[0] if cache_path.exists() else None
        if not latest_cache:
            raise RuntimeError("No cached reviews found. Please run ingestion first.")
            
        norm_path = latest_cache / "reviews_normalized.json"
        with open(norm_path) as f:
            raw_json = json.load(f)
            reviews = [Review(text=r["text"], rating=r["rating"]) for r in raw_json]

        if not reviews:
            raise ValueError("No reviews fetched")

        # 3. Pipeline
        logger.info("Phase 2: Analysis pipeline")
        report = analyze(reviews, run_context, pipeline_config)

        # 4. Render
        logger.info("Phase 3: Render")
        doc_section = build_doc_section(report, run_context)
        
        doc_url = ""
        # 5. Deliver Doc (Phase 4)
        if not run_context.dry_run:
            logger.info("Phase 4: Docs delivery")
            doc_result = append_doc_section(doc_section, product_config)
            doc_url = doc_result.get("doc_url", "")
            record_delivery(run_id, "google_doc", url=doc_url)
        else:
            logger.info("Dry run: skipping Docs delivery")

        # 6. Deliver Email (Phase 5)
        teaser = build_email_teaser(report, run_context, doc_url=doc_url)
        teaser.recipients = product_config.get("delivery", {}).get("email", {}).get("recipients", [])
        
        if not run_context.dry_run:
            logger.info("Phase 5: Email delivery")
            if check_delivery_exists(teaser.idempotency_key):
                logger.info("Email already delivered for this key. Skipping.")
            else:
                email_mode = run_context.email_mode
                logger.info(f"Email mode: {email_mode} (Sending to {len(teaser.recipients)} recipients)")
                email_result = send_email_teaser(teaser, email_mode=email_mode)
                record_delivery(
                    run_id, 
                    "gmail", 
                    external_id=email_result.get("draft_id"),
                    idempotency_key=teaser.idempotency_key
                )
        else:
            logger.info("Dry run: skipping Email delivery")

        # 7. Complete run
        report_json = json.dumps(asdict(report))
        complete_run(run_id, review_count=report.review_count, report_json=report_json)
        logger.info(f"Run {run_id} completed successfully")
        
        return {
            "status": "success",
            "run_id": run_id,
            "themes_count": len(report.themes),
            "doc_url": doc_url
        }

    except Exception as e:
        logger.exception("Run failed")
        fail_run(run_id, str(e))
        raise

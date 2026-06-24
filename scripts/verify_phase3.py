#!/usr/bin/env python3
"""Phase 3 verification script.

Loads Phase 1 cached reviews → runs Phase 2 pipeline → runs Phase 3 renderers.
Prints DocSection blocks and EmailTeaser content to stdout.

Usage:
    python scripts/verify_phase3.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Make sure the project root is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("verify_phase3")


def load_config():
    import yaml
    pipeline_path = Path("config/pipeline.yaml")
    product_path = Path("config/products/groww.yaml")
    pipeline_cfg = yaml.safe_load(pipeline_path.read_text())
    product_cfg = yaml.safe_load(product_path.read_text())
    return pipeline_cfg, product_cfg


def load_cached_reviews():
    """Load reviews from the Phase 1 cache (most recent date)."""
    from pulse.ingestion.models import Review

    cache_root = Path("data/cache/groww")
    dates = sorted(cache_root.iterdir(), reverse=True)
    if not dates:
        raise RuntimeError("No Phase 1 cache found. Run Phase 1 first.")

    latest = dates[0]
    norm_path = latest / "reviews_normalized.json"
    logger.info(f"Loading from {norm_path}")

    raw = json.loads(norm_path.read_text())
    reviews = [Review(text=r["text"], rating=r["rating"]) for r in raw]
    logger.info(f"Loaded {len(reviews)} normalized reviews")
    return reviews


def main():
    pipeline_cfg, product_cfg = load_config()

    from pulse.ingestion.models import RunContext
    from pulse.pipeline import analyze
    from pulse.render.doc_section import build_doc_section
    from pulse.render.email_teaser import build_email_teaser

    reviews = load_cached_reviews()

    ctx = RunContext(
        product="groww",
        iso_week="2026-W26",
        window_weeks=product_cfg["ingestion"]["window_weeks"],
        dry_run=True,
        email_mode="draft",
    )

    # ── Phase 2 ───────────────────────────────────────────────────────────────
    logger.info("Running Phase 2 analysis pipeline…")
    report = analyze(reviews, ctx, pipeline_cfg)
    logger.info(
        f"Phase 2 complete: {len(report.themes)} themes, "
        f"{sum(len(t.quotes) for t in report.themes)} validated quotes"
    )

    # ── Phase 3a — DocSection ─────────────────────────────────────────────────
    logger.info("Building DocSection…")
    doc = build_doc_section(report, ctx)

    print("\n" + "=" * 70)
    print("  PHASE 3a — DocSection")
    print("=" * 70)
    print(f"  anchor      : {doc.anchor}")
    print(f"  heading_text: {doc.heading_text}")
    print(f"  blocks      : {len(doc.blocks)} total")
    print()
    for block in doc.blocks:
        btype = block["type"]
        if btype == "divider":
            print("  ──────────────────────────────────────")
        elif btype == "heading1":
            print(f"\n  # {block['text']}")
        elif btype == "heading2":
            print(f"\n  ## {block['text']}")
        elif btype == "paragraph":
            print(f"  {block['text']}")
        elif btype == "bullet":
            print(f"  • {block['text']}")

    # ── Phase 3b — EmailTeaser ────────────────────────────────────────────────
    logger.info("Building EmailTeaser…")
    fake_doc_url = "https://docs.google.com/document/d/SAMPLE_DOC_ID#heading=groww-2026-W26"
    teaser = build_email_teaser(report, ctx, doc_url=fake_doc_url)

    print("\n" + "=" * 70)
    print("  PHASE 3b — EmailTeaser")
    print("=" * 70)
    print(f"  subject         : {teaser.subject}")
    print(f"  idempotency_key : {teaser.idempotency_key}")
    print(f"  recipients      : {teaser.recipients}")
    print()
    print("  ── PLAIN TEXT ──")
    print(teaser.text_body)
    print()
    print(f"  ── HTML ({len(teaser.html_body)} chars) ── (first 500 chars shown)")
    print(teaser.html_body[:500] + "…")

    # ── Save outputs ──────────────────────────────────────────────────────────
    out_dir = Path("data/render_preview")
    out_dir.mkdir(parents=True, exist_ok=True)

    doc_path = out_dir / "doc_section.json"
    doc_path.write_text(json.dumps(
        {"anchor": doc.anchor, "heading_text": doc.heading_text, "blocks": doc.blocks},
        indent=2,
        ensure_ascii=False,
    ))
    logger.info(f"DocSection saved → {doc_path}")

    email_path = out_dir / "email_teaser.html"
    email_path.write_text(teaser.html_body)
    logger.info(f"Email HTML saved → {email_path}")

    text_path = out_dir / "email_teaser.txt"
    text_path.write_text(teaser.text_body)
    logger.info(f"Email plain text saved → {text_path}")

    print("\n✅  Phase 3 complete. Outputs in data/render_preview/")


if __name__ == "__main__":
    main()

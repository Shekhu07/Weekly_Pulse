"""Pulse CLI — entry point for the Weekly Product Review Pulse.

Usage:
    python -m pulse.cli run --product groww [--iso-week 2026-W23]
    python -m pulse.cli dry-run --product groww
    python -m pulse.cli backfill --product groww --from-week 2026-W01 --to-week 2026-W20
    python -m pulse.cli status --product groww [--iso-week 2026-W23]
"""

from __future__ import annotations

from datetime import date

import click
from dotenv import load_dotenv

from pulse.config import load_product_config, load_pipeline_config
from pulse.ingestion.models import RunContext


# Load .env at CLI startup
load_dotenv()


def _current_iso_week() -> str:
    """Return the current ISO week as 'YYYY-Www'."""
    today = date.today()
    iso = today.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


@click.group()
@click.version_option(version="0.1.0", prog_name="pulse")
def cli():
    """Weekly Product Review Pulse — Automated review insights pipeline."""
    pass


@cli.command()
@click.option("--product", required=True, help="Product slug (e.g. 'groww').")
@click.option("--iso-week", default=None, help="ISO week (e.g. '2026-W23'). Defaults to current week.")
@click.option("--email-mode", default=None, type=click.Choice(["draft", "send"]), help="Override email mode.")
def run(product: str, iso_week: str | None, email_mode: str | None):
    """Run the full pulse pipeline for a product and week."""
    product_config = load_product_config(product)
    pipeline_config = load_pipeline_config()

    iso_week = iso_week or _current_iso_week()
    mode = email_mode or product_config.get("delivery", {}).get("email", {}).get("default_mode", "draft")

    ctx = RunContext(
        product=product,
        iso_week=iso_week,
        window_weeks=product_config.get("ingestion", {}).get("window_weeks", 10),
        dry_run=False,
        email_mode=mode,
    )

    click.echo(f"🚀 Pulse run: {ctx.product} / {ctx.iso_week} (email_mode={ctx.email_mode})")
    click.echo(f"   Window: {ctx.window_weeks} weeks")
    click.echo(f"   Product config: {product_config['display_name']}")
    click.echo(f"   Pipeline: {pipeline_config['summarization']['model']}")
    click.echo()
    
    from pulse.agent.orchestrator import execute_run
    try:
        summary = execute_run(ctx, product_config, pipeline_config)
        click.echo(f"\n✅  Run complete: {summary['status']}")
        if summary.get("doc_url"):
            click.echo(f"   Doc URL: {summary['doc_url']}")
    except Exception as e:
        click.secho(f"\n❌  Run failed: {e}", fg="red", err=True)


@cli.command("dry-run")
@click.option("--product", required=True, help="Product slug (e.g. 'groww').")
@click.option("--iso-week", default=None, help="ISO week. Defaults to current week.")
def dry_run(product: str, iso_week: str | None):
    """Run the full pipeline without MCP delivery writes."""
    product_config = load_product_config(product)
    pipeline_config = load_pipeline_config()

    iso_week = iso_week or _current_iso_week()

    ctx = RunContext(
        product=product,
        iso_week=iso_week,
        window_weeks=product_config.get("ingestion", {}).get("window_weeks", 10),
        dry_run=True,
        email_mode="draft",
    )

    click.echo(f"🧪 Pulse dry-run: {ctx.product} / {ctx.iso_week}")
    click.echo(f"   Window: {ctx.window_weeks} weeks | dry_run=True")
    click.echo()
    
    from pulse.agent.orchestrator import execute_run
    try:
        summary = execute_run(ctx, product_config, pipeline_config)
        click.echo(f"\n✅  Dry-run complete: {summary['status']}")
    except Exception as e:
        click.secho(f"\n❌  Dry-run failed: {e}", fg="red", err=True)


@cli.command()
@click.option("--product", required=True, help="Product slug.")
@click.option("--from-week", required=True, help="Start ISO week (e.g. '2026-W01').")
@click.option("--to-week", required=True, help="End ISO week (e.g. '2026-W20').")
def backfill(product: str, from_week: str, to_week: str):
    """Sequential backfill across a range of ISO weeks."""
    product_config = load_product_config(product)
    pipeline_config = load_pipeline_config()

    click.echo(f"📦 Pulse backfill: {product} / {from_week} → {to_week}")
    click.echo()
    
    # Simple week generator (e.g., 2026-W01 to 2026-W20)
    start_year, start_week = int(from_week[:4]), int(from_week[-2:])
    end_year, end_week = int(to_week[:4]), int(to_week[-2:])
    
    from pulse.agent.orchestrator import execute_run
    
    y, w = start_year, start_week
    while (y < end_year) or (y == end_year and w <= end_week):
        iso_week = f"{y}-W{w:02d}"
        ctx = RunContext(
            product=product,
            iso_week=iso_week,
            window_weeks=product_config.get("ingestion", {}).get("window_weeks", 10),
            dry_run=False,
            email_mode="draft",
        )
        click.echo(f"\n▶️  Backfilling: {iso_week}")
        try:
            summary = execute_run(ctx, product_config, pipeline_config)
            click.echo(f"   ✅ Status: {summary['status']}")
        except Exception as e:
            click.secho(f"   ❌ Failed: {e}", fg="red", err=True)
            
        w += 1
        if w > 52:  # Simplifying to 52 weeks per year
            w = 1
            y += 1


@cli.command()
@click.option("--product", required=True, help="Product slug.")
@click.option("--iso-week", default=None, help="ISO week. Shows all if omitted.")
def status(product: str, iso_week: str | None):
    """Show run ledger entries and delivery IDs."""
    load_product_config(product)  # Validate config exists

    from pulse.ledger.db import init_db, _get_db_path
    import sqlite3
    init_db()

    if iso_week:
        click.echo(f"📊 Pulse status: {product} / {iso_week}")
        query = "SELECT * FROM runs WHERE product = ? AND iso_week = ? ORDER BY started_at DESC"
        params = (product, iso_week)
    else:
        click.echo(f"📊 Pulse status: {product} (all weeks)")
        query = "SELECT * FROM runs WHERE product = ? ORDER BY started_at DESC LIMIT 20"
        params = (product,)
        
    click.echo("-" * 80)
    click.echo(f"{'RUN ID':<36} | {'WEEK':<8} | {'STATUS':<10} | {'REVIEWS':<7} | {'STARTED AT'}")
    click.echo("-" * 80)
    
    with sqlite3.connect(_get_db_path()) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(query, params)
        for row in cur.fetchall():
            click.echo(f"{row['run_id']:<36} | {row['iso_week']:<8} | {row['status']:<10} | {row['review_count']:<7} | {row['started_at']}")
            
            # Fetch deliveries
            d_cur = conn.execute("SELECT * FROM deliveries WHERE run_id = ?", (row['run_id'],))
            deliveries = d_cur.fetchall()
            if deliveries:
                for d in deliveries:
                    click.echo(f"    ↳ Delivery: {d['channel']} | ID: {d['external_id']} | URL: {d['url']}")
    click.echo("-" * 80)


if __name__ == "__main__":
    cli()

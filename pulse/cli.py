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
    click.echo("⚠️  Orchestrator not implemented yet (Phase 6). Exiting.")


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
    click.echo("⚠️  Orchestrator not implemented yet (Phase 6). Exiting.")


@cli.command()
@click.option("--product", required=True, help="Product slug.")
@click.option("--from-week", required=True, help="Start ISO week (e.g. '2026-W01').")
@click.option("--to-week", required=True, help="End ISO week (e.g. '2026-W20').")
def backfill(product: str, from_week: str, to_week: str):
    """Sequential backfill across a range of ISO weeks."""
    load_product_config(product)  # Validate config exists

    click.echo(f"📦 Pulse backfill: {product} / {from_week} → {to_week}")
    click.echo()
    click.echo("⚠️  Orchestrator not implemented yet (Phase 6). Exiting.")


@cli.command()
@click.option("--product", required=True, help="Product slug.")
@click.option("--iso-week", default=None, help="ISO week. Shows all if omitted.")
def status(product: str, iso_week: str | None):
    """Show run ledger entries and delivery IDs."""
    load_product_config(product)  # Validate config exists

    if iso_week:
        click.echo(f"📊 Pulse status: {product} / {iso_week}")
    else:
        click.echo(f"📊 Pulse status: {product} (all weeks)")
    click.echo()
    click.echo("⚠️  Ledger not implemented yet (Phase 6). Exiting.")


if __name__ == "__main__":
    cli()

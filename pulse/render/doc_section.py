"""Google Doc section builder — Phase 3.

Transforms a PulseReport into structured content blocks
for appending to a Google Doc via MCP.

Block format
------------
Each block is a dict with a ``type`` key:

  {"type": "heading1", "text": "..."}
  {"type": "heading2", "text": "..."}
  {"type": "paragraph", "text": "..."}
  {"type": "bullet",    "text": "..."}
  {"type": "divider"}

The MCP client (Phase 4) translates these into the actual
API calls / plain-text payload understood by the server.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pulse.ingestion.models import DocSection, PulseReport, RunContext


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_doc_section(report: PulseReport, run_context: RunContext) -> DocSection:
    """Build a structured Doc section from a PulseReport.

    Section structure:
        Heading 1: {Product} — Weekly Review Pulse — {iso_week}
        Paragraph: Period, source, generated timestamp
        Heading 2: Top themes (bulleted list)
        Heading 2: Real user quotes (bulleted list)
        Heading 2: Action ideas (bulleted list)
        Heading 2: Who this helps (bullets)

    Args:
        report: Completed pulse analysis report.
        run_context: Current run parameters.

    Returns:
        DocSection with anchor, heading, and structured blocks.
    """
    display_name = run_context.product.capitalize()
    anchor = f"{run_context.product}-{run_context.iso_week}"
    heading_text = f"{display_name} — Weekly Review Pulse — {run_context.iso_week}"

    # Human-readable generation timestamp in IST (+05:30)
    try:
        gen_dt = datetime.fromisoformat(report.generated_at.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        gen_dt = datetime.now(timezone.utc)

    ist_offset = "+05:30"
    gen_str = gen_dt.strftime(f"%Y-%m-%d %H:%M IST")

    blocks: list[dict] = []

    # ── Title ────────────────────────────────────────────────────────────────
    blocks.append({"type": "heading1", "text": heading_text})

    # ── Period / metadata line ────────────────────────────────────────────────
    period_line = (
        f"Period: Last {report.window_weeks} weeks (rolling)  ·  "
        f"Source: Google Play Store  ·  "
        f"{report.review_count} reviews  ·  "
        f"Generated: {gen_str}"
    )
    blocks.append({"type": "paragraph", "text": period_line})

    # ── Top themes ────────────────────────────────────────────────────────────
    blocks.append({"type": "heading2", "text": "Top themes"})
    if report.themes:
        for theme in report.themes:
            blocks.append({
                "type": "bullet",
                "text": f"{theme.theme_name} — {theme.summary}",
            })
    else:
        blocks.append({"type": "bullet", "text": "No themes identified."})

    # ── Real user quotes ──────────────────────────────────────────────────────
    blocks.append({"type": "heading2", "text": "Real user quotes"})
    all_quotes = [q for theme in report.themes for q in theme.quotes]
    if all_quotes:
        for quote in all_quotes:
            blocks.append({"type": "bullet", "text": f'"{quote}"'})
    else:
        blocks.append({"type": "bullet", "text": "No validated quotes available."})

    # ── Action ideas ──────────────────────────────────────────────────────────
    blocks.append({"type": "heading2", "text": "Action ideas"})
    all_actions = [a for theme in report.themes for a in theme.action_ideas]
    if all_actions:
        for action in all_actions:
            blocks.append({
                "type": "bullet",
                "text": f"{action.title} — {action.detail}",
            })
    else:
        blocks.append({"type": "bullet", "text": "No action ideas available."})

    # ── Who this helps ────────────────────────────────────────────────────────
    blocks.append({"type": "heading2", "text": "Who this helps"})
    blocks.append({
        "type": "bullet",
        "text": (
            "Product — Prioritise roadmap items backed by real user pain points "
            "and cluster-ranked severity."
        ),
    })
    blocks.append({
        "type": "bullet",
        "text": (
            "Support — Understand top complaint categories to craft better "
            "response templates and escalation triggers."
        ),
    })
    blocks.append({
        "type": "bullet",
        "text": (
            "Leadership — Get a weekly signal on app sentiment without reading "
            "thousands of individual reviews."
        ),
    })

    # ── Trailing divider ──────────────────────────────────────────────────────
    blocks.append({"type": "divider"})

    return DocSection(
        anchor=anchor,
        heading_text=heading_text,
        blocks=blocks,
    )

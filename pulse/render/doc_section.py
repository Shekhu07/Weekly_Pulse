"""Google Doc section builder — Phase 3.

Transforms a PulseReport into structured plain-text content
for appending to a Google Doc via MCP.

The MCP server currently supports appending plain text.
We format the content using markdown-like conventions.
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
        DocSection with anchor, heading, and plain text content.
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

    lines: list[str] = []

    # ── Title ────────────────────────────────────────────────────────────────
    lines.append(heading_text)
    lines.append("=" * len(heading_text))
    lines.append("")

    # ── Period / metadata line ────────────────────────────────────────────────
    period_line = (
        f"Period: Last {report.window_weeks} weeks (rolling)  ·  "
        f"Source: Google Play Store  ·  "
        f"{report.review_count} reviews  ·  "
        f"Generated: {gen_str}"
    )
    lines.append(period_line)
    lines.append("")

    # ── Top themes ────────────────────────────────────────────────────────────
    lines.append("Top themes")
    lines.append("-" * 10)
    if report.themes:
        for theme in report.themes:
            lines.append(f"• {theme.theme_name} — {theme.summary}")
    else:
        lines.append("• No themes identified.")
    lines.append("")

    # ── Real user quotes ──────────────────────────────────────────────────────
    lines.append("Real user quotes")
    lines.append("-" * 16)
    all_quotes = [q for theme in report.themes for q in theme.quotes]
    if all_quotes:
        for quote in all_quotes:
            lines.append(f"• \"{quote}\"")
    else:
        lines.append("• No validated quotes available.")
    lines.append("")

    # ── Action ideas ──────────────────────────────────────────────────────────
    lines.append("Action ideas")
    lines.append("-" * 12)
    all_actions = [a for theme in report.themes for a in theme.action_ideas]
    if all_actions:
        for action in all_actions:
            lines.append(f"• {action.title} — {action.detail}")
    else:
        lines.append("• No action ideas available.")
    lines.append("")

    # ── Who this helps ────────────────────────────────────────────────────────
    lines.append("Who this helps")
    lines.append("-" * 14)
    lines.append(
        "• Product — Prioritise roadmap items backed by real user pain points "
        "and cluster-ranked severity."
    )
    lines.append(
        "• Support — Understand top complaint categories to craft better "
        "response templates and escalation triggers."
    )
    lines.append(
        "• Leadership — Get a weekly signal on app sentiment without reading "
        "thousands of individual reviews."
    )
    lines.append("")
    
    # ── Trailing divider ──────────────────────────────────────────────────────
    lines.append("──────────────────────────────────────")
    lines.append("")

    return DocSection(
        anchor=anchor,
        heading_text=heading_text,
        content="\n".join(lines),
    )


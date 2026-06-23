"""Email teaser builder — Phase 3.

Builds a short stakeholder notification email with theme
headlines and a deep link to the Google Doc section.
"""

from __future__ import annotations

from pulse.ingestion.models import PulseReport, RunContext, EmailTeaser


def build_email_teaser(
    report: PulseReport,
    run_context: RunContext,
    doc_url: str = "",
) -> EmailTeaser:
    """Build an email teaser from a PulseReport.

    Email structure:
        Subject: {Product} Weekly Review Pulse — {iso_week}
        Body: 3–5 bullet theme headlines + context
        CTA: Read full report → {doc_url}
        Footer: timestamp, window, doc link

    Args:
        report: Completed pulse analysis report.
        run_context: Current run parameters.
        doc_url: URL to the Doc section (from Docs MCP).

    Returns:
        EmailTeaser with subject, html_body, text_body, recipients.

    Raises:
        NotImplementedError: Stub — implemented in Phase 3.
    """
    raise NotImplementedError("Email teaser builder not yet implemented (Phase 3)")

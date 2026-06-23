"""Google Doc section builder — Phase 3.

Transforms a PulseReport into structured content blocks
for appending to a Google Doc via MCP.
"""

from __future__ import annotations

from pulse.ingestion.models import PulseReport, RunContext, DocSection


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

    Raises:
        NotImplementedError: Stub — implemented in Phase 3.
    """
    raise NotImplementedError("Doc section builder not yet implemented (Phase 3)")

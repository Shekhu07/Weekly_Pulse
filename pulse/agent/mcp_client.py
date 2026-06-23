"""MCP client — Phase 4 & 5.

Connects to external MCP servers for Google Docs and Gmail delivery.
The pulse agent never holds Google OAuth credentials directly.
"""

from __future__ import annotations

from pulse.ingestion.models import DocSection, EmailTeaser


def append_doc_section(doc_section: DocSection, product_config: dict) -> dict:
    """Append a weekly section to the Google Doc via MCP server.

    Args:
        doc_section: Structured content to append.
        product_config: Product config with google_doc_id.

    Returns:
        Dict with doc_url, heading_id, revision_id.

    Raises:
        NotImplementedError: Stub — implemented in Phase 4.
    """
    raise NotImplementedError("Docs MCP client not yet implemented (Phase 4)")


def send_email_teaser(email_teaser: EmailTeaser) -> dict:
    """Create a draft or send an email via Gmail MCP server.

    Args:
        email_teaser: Email content with recipients and idempotency key.

    Returns:
        Dict with message_id or draft_id.

    Raises:
        NotImplementedError: Stub — implemented in Phase 5.
    """
    raise NotImplementedError("Gmail MCP client not yet implemented (Phase 5)")

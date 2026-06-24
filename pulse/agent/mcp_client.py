"""MCP client — Phase 4 & 5.

Connects to external MCP servers for Google Docs and Gmail delivery.
The pulse agent never holds Google OAuth credentials directly.
"""

from __future__ import annotations

import logging
import time

import httpx

from pulse.config import get_env_var
from pulse.ingestion.models import DocSection, EmailTeaser

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_DELAY = 2


def _get_mcp_client() -> httpx.Client:
    url = get_env_var("MCP_SERVER_URL", default="https://map-server-abhishek-production.up.railway.app")
    api_key = get_env_var("MCP_API_KEY", required=False, default="")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    return httpx.Client(base_url=url, headers=headers, timeout=30.0)


def append_doc_section(doc_section: DocSection, product_config: dict) -> dict:
    """Append a weekly section to the Google Doc via MCP server.

    Args:
        doc_section: Structured content to append.
        product_config: Product config with google_doc_id.

    Returns:
        Dict with doc_url, heading_id, revision_id.
    """
    doc_id = product_config.get("delivery", {}).get("google_doc_id")
    if not doc_id:
        raise ValueError("google_doc_id not found in product config")

    payload = {
        "doc_id": doc_id,
        "content": doc_section.content
    }

    last_err = None
    with _get_mcp_client() as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = client.post("/append_to_doc", json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
                logger.info(f"Successfully appended to Google Doc: {doc_url}")
                
                return {
                    "doc_url": doc_url,
                    "response": data.get("response")
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403, 404):
                    # Fatal errors (auth, not found)
                    raise RuntimeError(f"Fatal Docs MCP error ({e.response.status_code}): {e.response.text}") from e
                last_err = e
            except httpx.RequestError as e:
                last_err = e
                
            logger.warning(f"Docs MCP append failed (attempt {attempt}/{_MAX_RETRIES}): {last_err}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)
                
    raise RuntimeError(f"Failed to append to Google Doc after {_MAX_RETRIES} attempts. Last error: {last_err}")


def send_email_teaser(email_teaser: EmailTeaser) -> dict:
    """Create a draft or send an email via Gmail MCP server.

    Args:
        email_teaser: Email content with recipients and idempotency key.

    Returns:
        Dict with message_id or draft_id.
    """
    if not email_teaser.recipients:
        raise ValueError("No recipients specified for email teaser")
        
    payload = {
        "to": ", ".join(email_teaser.recipients),
        "subject": email_teaser.subject,
        "body": email_teaser.text_body
    }

    last_err = None
    with _get_mcp_client() as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                resp = client.post("/create_email_draft", json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                logger.info(f"Successfully created email draft for {payload['to']}")
                
                return {
                    "draft_id": data.get("response", {}).get("id"),
                    "response": data.get("response")
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403, 400):
                    raise RuntimeError(f"Fatal Gmail MCP error ({e.response.status_code}): {e.response.text}") from e
                last_err = e
            except httpx.RequestError as e:
                last_err = e
                
            logger.warning(f"Gmail MCP draft creation failed (attempt {attempt}/{_MAX_RETRIES}): {last_err}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY)
                
    raise RuntimeError(f"Failed to create email draft after {_MAX_RETRIES} attempts. Last error: {last_err}")


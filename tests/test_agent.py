import pytest
from unittest.mock import patch, MagicMock
from pulse.agent.mcp_client import send_email_teaser, append_doc_section
from pulse.ingestion.models import EmailTeaser, DocSection
import httpx

@patch("pulse.agent.mcp_client.httpx.Client")
def test_send_email_teaser_draft(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # Setup mock response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": {"id": "draft_123"}}
    mock_resp.raise_for_status.return_value = None
    mock_client.post.return_value = mock_resp
    
    teaser = EmailTeaser(
        subject="Test Subject",
        text_body="Test Body",
        html_body="<p>Test Body</p>",
        idempotency_key="test-key"
    )
    teaser.recipients = ["test@example.com"]
    
    result = send_email_teaser(teaser, email_mode="draft")
    
    assert result["draft_id"] == "draft_123"
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "/create_email_draft"
    assert kwargs["json"]["to"] == "test@example.com"
    assert kwargs["json"]["subject"] == "Test Subject"
    assert kwargs["json"]["body"] == "Test Body"

@patch("pulse.agent.mcp_client.httpx.Client")
def test_send_email_teaser_send(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # Setup mock response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": {"id": "msg_123"}}
    mock_resp.raise_for_status.return_value = None
    mock_client.post.return_value = mock_resp
    
    teaser = EmailTeaser(
        subject="Test Subject",
        text_body="Test Body",
        html_body="<p>Test Body</p>",
        idempotency_key="test-key"
    )
    teaser.recipients = ["test@example.com"]
    
    result = send_email_teaser(teaser, email_mode="send")
    
    assert result["message_id"] == "msg_123"
    mock_client.post.assert_called_once()
    args, kwargs = mock_client.post.call_args
    assert args[0] == "/send_email"

@patch("pulse.agent.mcp_client.httpx.Client")
def test_append_doc_section_idempotent(mock_client_class, mock_product_config):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client
    
    # Setup mock response for search_doc to return a found section (idempotent skip)
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "found": True
    }
    mock_resp.raise_for_status.return_value = None
    mock_client.post.return_value = mock_resp
    
    section = DocSection(
        anchor="groww-2026-W23",
        heading_text="Groww — Weekly Review Pulse — 2026-W23",
        content="Test content"
    )
    
    result = append_doc_section(section, mock_product_config)
    
    # Should return early with the found doc_url, and NOT call append_to_doc
    assert result["doc_url"] == "https://docs.google.com/document/d/test_doc_id/edit"
    assert result["response"]["note"] == "Already existed, skipped append"
    
    # Verify post was called exactly once (for search_doc)
    assert mock_client.post.call_count == 1
    args, kwargs = mock_client.post.call_args
    assert args[0] == "/search_doc"

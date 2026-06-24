import pytest
from unittest.mock import patch, MagicMock
from pulse.pipeline.scrubber import _redact_text
from pulse.pipeline.quote_validator import validate_quotes
from pulse.ingestion.models import Review, Theme

def test_scrub_pii():
    text = "My phone is 9876543210 and my PAN is ABCDE1234F. Email me at test@example.com."
    scrubbed, _ = _redact_text(text)
    
    assert "9876543210" not in scrubbed
    assert "ABCDE1234F" not in scrubbed
    assert "test@example.com" not in scrubbed
    
    assert "[PHONE]" in scrubbed
    assert "[ID]" in scrubbed
    assert "[EMAIL]" in scrubbed

def test_validate_quotes():
    reviews = [
        Review(
            text="The app crashes every time I try to login.",
            rating=1
        )
    ]
    
    theme = Theme(
        theme_name="Crashing",
        summary="Users report crashes.",
        quotes=["The app crashes every time I try to login.", "This is made up.", "APP crashes every TIME..."]
    )
    
    valid_theme = validate_quotes(theme, reviews, reviews)
    valid_quotes = valid_theme.quotes
    
    # "The app crashes every time I try to login." is an exact match.
    # "This is made up." is fabricated and should be dropped.
    # "APP crashes every TIME..." is a case-insensitive match with ellipsis, should be kept.
    assert len(valid_quotes) == 2
    assert "The app crashes every time I try to login." in valid_quotes
    assert "APP crashes every TIME..." in valid_quotes
    assert "This is made up." not in valid_quotes

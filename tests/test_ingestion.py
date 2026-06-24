import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from pulse.ingestion.normalizer import normalize_reviews
from pulse.ingestion.models import Review

def test_filter_and_normalize(sample_raw_reviews):
    config = {
        "min_words": 5,
        "allowed_language": "en"
    }
    
    normalized = normalize_reviews(sample_raw_reviews, {"ingestion": config})
    
    # Review 1 and 2 should pass.
    # Review 3 should fail (Too short - 2 words).
    # Review 4 should pass.
    assert len(normalized) == 3
    
    # Check text of passed reviews
    passed_texts = [r.text for r in normalized]
    assert "The app crashes every time I try to login. Very frustrating experience." in passed_texts
    assert "I love this app! It's so easy to use and the interface is great." in passed_texts
    assert "My number is 9876543210 and my email is test@example.com. Please fix the bug." in passed_texts
    assert "Too short" not in passed_texts

@patch("pulse.ingestion.play_store.reviews")
def test_fetch_reviews_caching(mock_reviews, mock_run_context, mock_product_config):
    from pulse.ingestion.play_store import fetch_reviews
    
    # Setup mock to return two dummy reviews and no continuation token
    mock_reviews.return_value = (
        [
            {
                "content": "Great app",
                "score": 5,
                "at": datetime(2026, 6, 1)
            },
            {
                "content": "Terrible app",
                "score": 1,
                "at": datetime(2026, 6, 2)
            }
        ],
        None
    )
    
    # Call the function
    result = fetch_reviews(mock_product_config, mock_run_context)
    
    # Verify it returns our reviews
    assert len(result) == 2
    assert result[0].text == "Great app"
    
    # And mock was called
    mock_reviews.assert_called_once()

import pytest
from datetime import datetime
from pulse.ingestion.models import RawReview, Review, RunContext

@pytest.fixture
def mock_run_context():
    return RunContext(
        product="test_product",
        iso_week="2026-W23",
        window_weeks=10,
        dry_run=True,
        email_mode="draft"
    )

@pytest.fixture
def mock_product_config():
    return {
        "product": "test_product",
        "display_name": "Test Product",
        "play_store": {"app_id": "com.test.app"},
        "ingestion": {
            "window_weeks": 10,
            "min_reviews": 2,
            "max_reviews": 1000,
            "min_words": 5,
            "allowed_language": "en"
        },
        "delivery": {
            "google_doc_id": "test_doc_id",
            "email": {
                "recipients": ["test@example.com"],
                "default_mode": "draft"
            }
        }
    }

@pytest.fixture
def sample_raw_reviews():
    return [
        RawReview(
            text="The app crashes every time I try to login. Very frustrating experience.",
            rating=1,
            published_at="2026-06-01T00:00:00Z"
        ),
        RawReview(
            text="I love this app! It's so easy to use and the interface is great.",
            rating=5,
            published_at="2026-06-02T00:00:00Z"
        ),
        RawReview(
            text="Too short",
            rating=3,
            published_at="2026-06-03T00:00:00Z"
        ),
        RawReview(
            text="My number is 9876543210 and my email is test@example.com. Please fix the bug.",
            rating=2,
            published_at="2026-06-04T00:00:00Z"
        )
    ]

@pytest.fixture
def sample_normalized_reviews():
    return [
        Review(
            text="The app crashes every time I try to login. Very frustrating experience.",
            rating=1
        ),
        Review(
            text="I love this app! It's so easy to use and the interface is great.",
            rating=5
        ),
        Review(
            text="My number is [PHONE] and my email is [EMAIL]. Please fix the bug.",
            rating=2
        )
    ]

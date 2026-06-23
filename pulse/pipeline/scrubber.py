"""PII scrubbing & language filtering — Phase 2a.

Two-step pipeline run before embedding, LLM calls, and publishing:
  Step 1: Drop non-Latin-dominant reviews (Devanagari/Indic script)
  Step 2: Redact PII patterns (email, phone, ID, token URLs)
"""

from __future__ import annotations

import logging
import re

from pulse.ingestion.models import Review

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Step 1 — Language / script filter
# ---------------------------------------------------------------------------

def is_latin_dominant(text: str) -> bool:
    """Return True if >= 80% of characters are ASCII.

    Keeps Hinglish (Hindi in Latin script) but drops Devanagari/Indic-script
    reviews that slipped through the Play Store lang=en filter.
    Real Groww data: 14 Devanagari reviews out of 1,066 normalized (1.3%).
    """
    if not text:
        return True
    ascii_chars = sum(1 for c in text if c.isascii())
    return (ascii_chars / len(text)) >= 0.80


# ---------------------------------------------------------------------------
# Step 2 — PII redaction patterns
# ---------------------------------------------------------------------------

# Email addresses
_EMAIL_RE = re.compile(
    r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE,
)

# Indian mobile numbers:
#   +91-XXXXXXXXXX, +91 XXXXXXXXXX, 91XXXXXXXXXX, 0XXXXXXXXXX, XXXXXXXXXX (10 digits)
_PHONE_RE = re.compile(
    r'(?:\+91[\s\-]?|0)?[6-9]\d{9}\b',
)

# PAN: 5 uppercase letters, 4 digits, 1 uppercase letter (ABCDE1234F)
_PAN_RE = re.compile(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b')

# Aadhaar: 12-digit number (with optional spaces/dashes every 4 digits)
_AADHAAR_RE = re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b')

# Generic long numeric sequence (10-16 digits) — catches account/card numbers
_LONG_NUM_RE = re.compile(r'\b\d{10,16}\b')

# URLs — redact path and query string, keep domain for context
_URL_RE = re.compile(
    r'https?://[^\s/]+(/[^\s]*)?',
    re.IGNORECASE,
)


def _redact_text(text: str) -> tuple[str, dict[str, int]]:
    """Apply all PII redaction patterns and return (clean_text, redaction_counts)."""
    counts: dict[str, int] = {}

    def replace_count(pattern: re.Pattern, replacement: str, label: str) -> None:
        nonlocal text
        matches = pattern.findall(text)
        if matches:
            counts[label] = counts.get(label, 0) + len(matches)
            text = pattern.sub(replacement, text)

    # Order matters: emails before phone (emails have @ which protects them from phone regex)
    replace_count(_EMAIL_RE, '[EMAIL]', 'email')
    replace_count(_PHONE_RE, '[PHONE]', 'phone')
    replace_count(_PAN_RE, '[ID]', 'pan')
    replace_count(_AADHAAR_RE, '[ID]', 'aadhaar')
    replace_count(_LONG_NUM_RE, '[ID]', 'long_num')
    replace_count(_URL_RE, '[URL]', 'url')

    return text, counts


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrub_reviews(reviews: list[Review]) -> list[Review]:
    """Script-filter and PII-scrub a list of normalized reviews.

    Returns a NEW list of Review objects (originals unchanged).
    Logs per-run stats: script-dropped count + PII redaction counts per pattern.

    Args:
        reviews: Normalized reviews from Phase 1.

    Returns:
        Scrubbed reviews safe for embedding and LLM prompting.
    """
    script_dropped = 0
    total_redactions: dict[str, int] = {}
    result: list[Review] = []

    for review in reviews:
        # Step 1: language / script filter
        if not is_latin_dominant(review.text):
            script_dropped += 1
            continue

        # Step 2: PII redaction
        clean_text, redactions = _redact_text(review.text)
        for key, count in redactions.items():
            total_redactions[key] = total_redactions.get(key, 0) + count

        result.append(Review(text=clean_text, rating=review.rating))

    logger.info(
        f"Scrubber: {len(reviews)} in → {script_dropped} script-dropped, "
        f"{len(result)} out | PII redactions: {total_redactions}"
    )
    return result

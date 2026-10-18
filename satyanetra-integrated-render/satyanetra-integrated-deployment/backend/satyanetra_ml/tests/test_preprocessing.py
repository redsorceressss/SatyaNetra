"""
Unit tests for text preprocessing, normalization, and entity extraction.
"""

from src.preprocessing import (
    clean_for_vectorizer,
    extract_financial_entities,
    is_usable_query,
    normalize_text,
)


def test_normalize_text_whitespace_and_unicode():
    """Verify whitespace collapsing and NFKC unicode normalization."""
    raw = "  Officer   demanded  a   bribe \t\n\r  of ₹50,000.  "
    expected = "Officer demanded a bribe of ₹50,000."
    assert normalize_text(raw) == expected

    # Unicode full-width characters
    raw_unicode = "ＣＢＩ ｏｆｆｉｃｅｒ"
    assert normalize_text(raw_unicode) == "CBI officer"


def test_normalize_text_null_and_empty():
    """Verify safe handling of None and empty inputs."""
    assert normalize_text(None) == ""
    assert normalize_text("") == ""
    assert normalize_text("   ") == ""


def test_clean_for_vectorizer():
    """Verify lowercasing and currency token preservation for TF-IDF."""
    raw = "Bribe of ₹25,000 and $500 cash demanded."
    cleaned = clean_for_vectorizer(raw)
    assert "inr_currency" in cleaned
    assert "usd_currency" in cleaned
    assert "bribe" in cleaned
    assert cleaned.islower()


def test_is_usable_query_validation():
    """Verify comprehensive boundary and safety checks for queries."""
    # Valid query
    usable, msg = is_usable_query("Electricity board official demanded money to clear challan.")
    assert usable is True
    assert msg == ""

    # Null / empty
    usable, msg = is_usable_query(None)
    assert usable is False

    usable, msg = is_usable_query("   ")
    assert usable is False

    # Too short
    usable, msg = is_usable_query("ok", min_length=3)
    assert usable is False
    assert "too short" in msg

    # Punctuation only
    usable, msg = is_usable_query("!?!?!?...", min_length=3)
    assert usable is False
    assert "punctuation" in msg

    # Exceeding max length
    usable, msg = is_usable_query("a" * 100, max_length=50)
    assert usable is False
    assert "exceeds maximum" in msg


def test_extract_financial_entities():
    """Verify extraction of URLs, emails, phone numbers, and monetary figures."""
    text = (
        "Contact officer at verify@acb-dept.gov.in or call +919876543210. "
        "Visit https://portal.example.org/pay. He demanded ₹30,000 or $5000 immediately."
    )
    entities = extract_financial_entities(text)

    assert "https://portal.example.org/pay" in entities["urls"]
    assert "verify@acb-dept.gov.in" in entities["emails"]
    assert any("9876543210" in p for p in entities["phone_numbers"])
    assert any("30,000" in m or "5000" in m for m in entities["monetary_mentions"])

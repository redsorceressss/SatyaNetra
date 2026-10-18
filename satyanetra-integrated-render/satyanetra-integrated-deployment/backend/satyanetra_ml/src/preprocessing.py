"""
Text preprocessing and entity extraction module for SatyaNetra ML Engine.
Normalizes incident text while preserving scam indicators, currencies, numbers, and identifiers.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple


# Regex patterns for scam-relevant entity extraction
RE_URL = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
RE_PHONE = re.compile(r"(?:\+?91[\s-]?)?[6-9]\d{9}\b|\b(?:\+?1[\s-]?)?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{4}\b")
RE_CURRENCY = re.compile(
    r"(?:₹|Rs\.?|INR|\$|USD)\s*\d+(?:[.,]\d+)*(?:\s*(?:lakh|crore|thousand|k|million|bn|crores|lakhs))?"
    r"|\b\d+(?:[.,]\d+)*\s*(?:lakh|crore|rupees|dollars|inr|usd)\b",
    re.IGNORECASE,
)

# Whitespace cleaner
RE_MULTI_WHITESPACE = re.compile(r"[\s\u200b\u200e\u200f\ufeff]+")


def normalize_text(text: Optional[str]) -> str:
    """
    Safely clean and normalize input text.

    Preserves:
    - Financial amounts and currency symbols (₹, $, INR, USD).
    - Phone number formats and URLs.
    - Acronyms (OTP, PIN, KYC, FIR, ACB, Lokayukta, CBI).
    - Meaningful scam terms without stripping valuable lexical clues.

    Normalizes:
    - Unicode anomalies (NFKC decomposition).
    - Multiple consecutive spaces, tabs, and carriage returns into single spaces.
    """
    if text is None or not isinstance(text, str):
        return ""

    # Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)

    # Collapse excessive whitespace
    normalized = RE_MULTI_WHITESPACE.sub(" ", normalized).strip()

    return normalized


def clean_for_vectorizer(text: Optional[str]) -> str:
    """
    Preprocess text specifically for TF-IDF tokenization.
    Normalizes case and removes abrasive symbols while keeping words, numbers, and currency keywords.
    """
    raw = normalize_text(text)
    if not raw:
        return ""

    # Replace currency symbols with text tokens so TF-IDF can leverage them
    cleaned = raw.replace("₹", " inr_currency ").replace("$", " usd_currency ")
    # Lowercase for consistent vocabulary mapping
    return cleaned.lower()


def is_usable_query(text: Optional[str], min_length: int = 3, max_length: int = 10000) -> Tuple[bool, str]:
    """
    Validate whether query text is usable for similarity search.

    Returns:
    - (True, "") if query is valid and ready for processing.
    - (False, reason) if query is empty, whitespace-only, too short, or exceeds max length.
    """
    if text is None:
        return False, "Input report text is None."

    if not isinstance(text, str):
        return False, f"Expected string input, got {type(text).__name__}."

    normalized = normalize_text(text)

    if not normalized:
        return False, "Report text is empty or contains only whitespace."

    if len(normalized) < min_length:
        return False, f"Report text is too short ({len(normalized)} chars; minimum is {min_length})."

    # Check if string consists purely of punctuation with no alphanumeric characters
    if not any(c.isalnum() for c in normalized):
        return False, "Report text contains only punctuation or special symbols."

    if len(normalized) > max_length:
        return False, f"Report text exceeds maximum allowed length ({len(normalized)} > {max_length} chars)."

    return True, ""


def extract_financial_entities(text: Optional[str]) -> Dict[str, List[str]]:
    """
    Extract key scam-related entities (URLs, emails, phones, monetary values)
    without modifying the original text. Useful for explainability and forensic reporting.
    """
    normalized = normalize_text(text)
    if not normalized:
        return {
            "urls": [],
            "emails": [],
            "phone_numbers": [],
            "monetary_mentions": [],
        }

    raw_urls = RE_URL.findall(normalized)
    cleaned_urls = [u.rstrip(".,;:!?'\"") for u in raw_urls]
    urls = list(dict.fromkeys(u for u in cleaned_urls if u))
    emails = list(dict.fromkeys(RE_EMAIL.findall(normalized)))
    phones = list(dict.fromkeys(RE_PHONE.findall(normalized)))
    currencies = list(dict.fromkeys(RE_CURRENCY.findall(normalized)))

    return {
        "urls": urls,
        "emails": emails,
        "phone_numbers": phones,
        "monetary_mentions": currencies,
    }

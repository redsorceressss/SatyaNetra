"""Tests for the ML bridge. These need only scikit-learn (no FastAPI/DB)."""
from app.ml_service import analyze_report_text


def test_bridge_loads_full_expanded_dataset():
    r = analyze_report_text("Court staff arrested for taking Rs 40,000 bribe for a favourable court order in Rajasthan", top_k=3)
    assert r["status"] == "success"
    assert r["engine"]["reference_cases_indexed"] >= 18
    assert r["similar_cases"][0]["case_id"] == "IN-RJ-2026-001"


def test_bridge_handles_unrelated_text_without_inventing_matches():
    r = analyze_report_text("To bake a chocolate cake, preheat the oven and mix flour, cocoa and sugar.")
    assert r["matched_cases_count"] == 0
    assert r["risk_indicators"] == []

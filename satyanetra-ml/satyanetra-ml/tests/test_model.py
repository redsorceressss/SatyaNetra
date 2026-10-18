"""
Unit tests for the TF-IDF and Cosine-Similarity Engine.
"""

from src.data_loader import CaseRecord, load_cases
from src.model import ScamPatternSimilarityEngine


def test_engine_fit_and_query_ranking():
    """Verify fitting on real cases and accurate rank-ordering for a targeted query."""
    cases = load_cases()
    engine = ScamPatternSimilarityEngine()
    engine.fit(cases)
    assert engine.is_fitted is True

    # Electricity challan query should strongly match IN-MP-2025-001
    query_text = "Electricity department employees demanded a bribe to reduce my electricity theft challan."
    results = engine.query(query_text, top_k=3, threshold=0.0)

    assert len(results) > 0
    top_match = results[0]
    assert top_match["case_id"] == "IN-MP-2025-001"
    assert "Electricity-distribution" in top_match["case_title"]
    assert top_match["similarity_score"] > 0.15

    # Verify descending score order
    scores = [r["similarity_score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_top_k_limiting():
    """Verify that top_k strictly bounds the number of returned matches."""
    cases = load_cases()
    engine = ScamPatternSimilarityEngine().fit(cases)

    results_k1 = engine.query("official demanded cash bribe payment", top_k=1, threshold=0.0)
    assert len(results_k1) == 1

    results_k2 = engine.query("official demanded cash bribe payment", top_k=2, threshold=0.0)
    assert len(results_k2) == 2


def test_threshold_filtering():
    """Verify that cases below the configured threshold are excluded."""
    cases = load_cases()
    engine = ScamPatternSimilarityEngine().fit(cases)

    # With a high threshold, weak matches should be excluded
    results_high_cutoff = engine.query("police officer investigation", threshold=0.99)
    assert len(results_high_cutoff) == 0

    results_normal = engine.query("police officer investigation", threshold=0.05)
    assert len(results_normal) > 0


def test_empty_dataset_handling():
    """Verify that an empty dataset does not raise exceptions."""
    engine = ScamPatternSimilarityEngine()
    engine.fit([])
    assert engine.is_fitted is False

    res = engine.query("any incident text", top_k=5)
    assert res == []


def test_zero_vector_and_out_of_vocabulary():
    """Verify that queries with no vocabulary overlap return an empty list without error."""
    cases = load_cases()
    engine = ScamPatternSimilarityEngine().fit(cases)

    # Completely unrelated nonsense tokens
    res = engine.query("xyzqwerty foobarblatz 999888777", threshold=0.0)
    assert res == []


def test_deterministic_scoring():
    """Verify that the engine produces strictly deterministic scores across identical calls."""
    cases = load_cases()
    engine = ScamPatternSimilarityEngine().fit(cases)

    query = "Commercial driver's license bribery scheme with applicant payments."
    res1 = engine.query(query, top_k=3)
    res2 = engine.query(query, top_k=3)

    assert len(res1) == len(res2)
    for m1, m2 in zip(res1, res2):
        assert m1["case_id"] == m2["case_id"]
        assert m1["similarity_score"] == m2["similarity_score"]


def test_model_serialization_and_deserialization(tmp_path):
    """Verify saving and loading model artifacts with joblib."""
    cases = load_cases()
    engine = ScamPatternSimilarityEngine().fit(cases)

    save_path = tmp_path / "test_engine.joblib"
    engine.save(save_path)
    assert save_path.exists()

    loaded_engine = ScamPatternSimilarityEngine.load(save_path)
    assert loaded_engine.is_fitted is True
    assert len(loaded_engine.cases) == len(cases)

    # Query loaded engine and compare with original
    query = "School recognition application extension bribe demanded by coordinator"
    orig_res = engine.query(query, top_k=2)
    loaded_res = loaded_engine.query(query, top_k=2)

    assert orig_res == loaded_res

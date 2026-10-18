"""Thin bridge between the FastAPI app and the standalone `satyanetra_ml` engine.

The engine is loaded lazily on first use so the API still starts (and every other
endpoint keeps working) if the ML dependencies are missing. Report text is never
logged or stored here.
"""
from __future__ import annotations

import logging
from functools import lru_cache

logger = logging.getLogger("satyanetra.ml")


class MLUnavailableError(RuntimeError):
    """Raised when the ML engine cannot be imported or has no reference cases indexed."""


@lru_cache(maxsize=1)
def _get_analyzer():
    # lru_cache does not cache exceptions, so a failed start-up is retried on the next call.
    try:
        from satyanetra_ml.src.predict import ScamReportAnalyzer
    except Exception as exc:  # ImportError (e.g. scikit-learn missing) or config problems
        logger.exception("ML engine could not be imported")
        raise MLUnavailableError("ML engine is not available on this server") from exc

    analyzer = ScamReportAnalyzer()
    if not analyzer.engine.is_fitted:
        logger.error("ML engine started with no reference cases (check data/public_cases.json)")
        raise MLUnavailableError("ML engine has no reference cases loaded")
    return analyzer


def analyze_report_text(description: str, top_k: int = 5) -> dict:
    """Run similarity retrieval + explainable risk indicators on a report description."""
    analyzer = _get_analyzer()
    result = analyzer.analyze_report(description, top_k=top_k)
    result["engine"] = {
        "method": "tfidf_cosine_retrieval_and_rule_based_indicators",
        "reference_cases_indexed": len(analyzer.engine.cases),
    }
    return result

"""
Prediction and inference interface for SatyaNetra Scam-Pattern Similarity Engine.
Exposes a clean, high-level, JSON-serializable `analyze_report` function for CLI,
tests, and future FastAPI backend integration.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .config import EngineConfig, get_default_config
from .data_loader import load_cases
from .indicators import scan_risk_indicators
from .model import ScamPatternSimilarityEngine
from .preprocessing import extract_financial_entities, is_usable_query, normalize_text

logger = logging.getLogger(__name__)

DISCLAIMER_TEXT = (
    "Similarity scores reflect lexical overlap with curated public reference cases and are retrieval "
    "scores, not calibrated fraud probabilities. Risk indicators identify heuristic warning patterns "
    "for human review and do not constitute legal proof of fraud, guilt, or criminal intent."
)


class ScamReportAnalyzer:
    """
    High-level facade orchestrating reference-case retrieval and risk indicator evaluation.
    Maintains an in-memory fitted similarity engine.
    """

    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        engine: Optional[ScamPatternSimilarityEngine] = None,
    ) -> None:
        self.config = config or get_default_config()
        if engine and engine.is_fitted:
            self.engine = engine
        else:
            self.engine = ScamPatternSimilarityEngine(config=self.config)
            self._initialize_engine()

    def _initialize_engine(self) -> None:
        """Load public reference cases and fit the similarity model."""
        try:
            cases = load_cases(config=self.config, allow_empty=True)
            self.engine.fit(cases)
            logger.info("ScamReportAnalyzer initialized with %d reference cases.", len(cases))
        except Exception as exc:
            logger.exception("Failed to initialize ScamReportAnalyzer engine: %s", exc)

    def analyze_report(
        self,
        text: Optional[str],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a suspicious incident report description.

        Parameters:
        - text: Incident report text string.
        - top_k: Maximum number of similar reference cases to return.
        - threshold: Minimum cosine similarity score cutoff.

        Returns:
        - Clean, JSON-serializable dictionary with retrieval results, risk indicators,
          extracted entities, warnings, and disclaimers.
        """
        k = top_k if top_k is not None else self.config.default_top_k
        cutoff = threshold if threshold is not None else self.config.similarity_threshold

        # 1. Input Validation
        is_valid, validation_msg = is_usable_query(
            text,
            min_length=self.config.min_input_length,
            max_length=self.config.max_input_length,
        )

        if not is_valid:
            return {
                "status": "invalid_input",
                "input_length": len(text) if isinstance(text, str) else 0,
                "analysis_summary": f"Input validation failed: {validation_msg}",
                "matched_cases_count": 0,
                "similar_cases": [],
                "risk_indicators": [],
                "detected_entities": {
                    "urls": [],
                    "emails": [],
                    "phone_numbers": [],
                    "monetary_mentions": [],
                },
                "warnings": [validation_msg],
                "disclaimer": DISCLAIMER_TEXT,
            }

        normalized_text = normalize_text(text)
        warnings: List[str] = []

        # 2. Heuristic Risk Indicator Scan
        raw_indicators = scan_risk_indicators(normalized_text)
        indicators_json = [ind.to_dict() for ind in raw_indicators]

        # 3. Entity Extraction
        entities = extract_financial_entities(normalized_text)

        # 4. Lexical Similarity Retrieval
        similar_cases = self.engine.query(normalized_text, top_k=k, threshold=cutoff)

        # 5. Formulate Summary
        matched_count = len(similar_cases)
        ind_count = len(indicators_json)

        if matched_count > 0 and ind_count > 0:
            summary = (
                f"Identified {matched_count} similar reference case(s) and detected "
                f"{ind_count} risk indicator(s) in the report description."
            )
        elif matched_count > 0:
            summary = (
                f"Identified {matched_count} similar reference case(s) with lexical pattern overlap. "
                "No specific coercive or deceptive risk indicators detected."
            )
        elif ind_count > 0:
            summary = (
                f"Detected {ind_count} risk indicator(s) in the report description. "
                "No reference public cases met the retrieval similarity threshold."
            )
        else:
            summary = (
                "No reference public cases met the retrieval similarity threshold, and no specific "
                "risk indicators were detected."
            )

        return {
            "status": "success",
            "input_length": len(normalized_text),
            "analysis_summary": summary,
            "matched_cases_count": matched_count,
            "similar_cases": similar_cases,
            "risk_indicators": indicators_json,
            "detected_entities": entities,
            "warnings": warnings,
            "disclaimer": DISCLAIMER_TEXT,
        }


# Global lazy-loaded analyzer instance
_default_analyzer: Optional[ScamReportAnalyzer] = None


def get_default_analyzer() -> ScamReportAnalyzer:
    """Obtain or initialize the module-level singleton ScamReportAnalyzer."""
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = ScamReportAnalyzer()
    return _default_analyzer


def analyze_report(
    text: Optional[str],
    top_k: int = 5,
    threshold: Optional[float] = None,
    config: Optional[EngineConfig] = None,
) -> Dict[str, Any]:
    """
    Convenience function providing a stateless, functional interface for report analysis.
    This is the primary function to be called by external modules and future FastAPI endpoints.

    Parameters:
    - text: User-submitted report or incident description.
    - top_k: Maximum number of matches to retrieve (default 5).
    - threshold: Cosine similarity cutoff (default from config).
    - config: Optional EngineConfig override.

    Returns:
    - JSON-serializable dictionary with analysis results.
    """
    if config is not None:
        analyzer = ScamReportAnalyzer(config=config)
        return analyzer.analyze_report(text, top_k=top_k, threshold=threshold)

    return get_default_analyzer().analyze_report(text, top_k=top_k, threshold=threshold)

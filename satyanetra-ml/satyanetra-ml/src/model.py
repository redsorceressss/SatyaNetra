"""
Scam-Pattern Similarity Engine for SatyaNetra.
TF-IDF vectorization and cosine similarity pipeline with deterministic scoring,
robust zero-vector and empty-dataset handling, and explainable retrieval formatting.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import EngineConfig, get_default_config
from .data_loader import CaseRecord
from .preprocessing import clean_for_vectorizer, is_usable_query

logger = logging.getLogger(__name__)


class ScamPatternSimilarityEngine:
    """
    NLP Similarity retrieval engine comparing suspicious reports against curated public cases.

    NOTE: Similarity scores represent lexical retrieval proximity, NOT a legal finding
    or calibrated probability of fraud.
    """

    def __init__(self, config: Optional[EngineConfig] = None) -> None:
        self.config: EngineConfig = config or get_default_config()
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix: Optional[Any] = None
        self.cases: List[CaseRecord] = []
        self._is_fitted: bool = False

    @property
    def is_fitted(self) -> bool:
        """Check whether the vectorizer and case index have been initialized."""
        return self._is_fitted

    def fit(self, cases: List[CaseRecord]) -> "ScamPatternSimilarityEngine":
        """
        Fit the TF-IDF vectorizer and build the reference case index.

        Parameters:
        - cases: List of CaseRecord objects. Handles empty lists gracefully.

        Returns:
        - self (for fluent chaining)
        """
        if not cases:
            logger.warning("Empty case list provided to ScamPatternSimilarityEngine.fit(). Engine remains unfitted.")
            self.cases = []
            self.vectorizer = None
            self.tfidf_matrix = None
            self._is_fitted = False
            return self

        self.cases = list(cases)
        corpus = [clean_for_vectorizer(c.searchable_text) for c in self.cases]

        # Initialize vectorizer with configurable word n-grams and sublinear TF
        self.vectorizer = TfidfVectorizer(
            ngram_range=self.config.ngram_range,
            max_features=self.config.max_features,
            sublinear_tf=self.config.sublinear_tf,
            stop_words=self.config.stop_words,
            norm=self.config.norm,
            dtype=np.float32,
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
        self._is_fitted = True
        logger.info(
            "Fitted similarity engine on %d reference cases (vocabulary size: %d).",
            len(self.cases),
            len(self.vectorizer.vocabulary_),
        )
        return self

    def query(
        self,
        text: Optional[str],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute similarity between input report text and indexed reference cases.

        Parameters:
        - text: Incident report text.
        - top_k: Maximum number of matches to return (defaults to config.default_top_k).
        - threshold: Minimum cosine similarity score to qualify as a match.

        Returns:
        - Ranked list of matched reference case dictionaries in descending score order.
        """
        usable, _ = is_usable_query(
            text,
            min_length=self.config.min_input_length,
            max_length=self.config.max_input_length,
        )
        if not usable or not self._is_fitted or not self.cases or self.vectorizer is None or self.tfidf_matrix is None:
            return []

        cleaned_query = clean_for_vectorizer(text)
        query_vec = self.vectorizer.transform([cleaned_query])

        # Guard against zero-vector (out-of-vocabulary or non-informative query)
        if query_vec.nnz == 0:
            logger.debug("Query contains no terms in the reference case vocabulary.")
            return []

        # Cosine similarity matrix multiplication
        sims: np.ndarray = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        k = top_k if top_k is not None else self.config.default_top_k
        cutoff = threshold if threshold is not None else self.config.similarity_threshold

        # Rank descending
        ranked_indices = np.argsort(-sims)

        results: List[Dict[str, Any]] = []
        for idx in ranked_indices:
            score = float(sims[idx])
            if score < cutoff:
                # Array is sorted descending, so subsequent scores will also fall below cutoff
                break

            case = self.cases[idx]
            results.append({
                "case_id": case.id,
                "case_title": case.case_title,
                "category": case.category,
                "summary": case.summary,
                "similarity_score": round(score, 4),
                "source_url": case.source_url,
                "jurisdiction": case.jurisdiction,
                "state": case.state,
                "city": case.city,
                "case_status": case.case_status,
                "status_basis": case.status_basis,
                "source_publisher": case.source_publisher,
                "source_published_date": case.source_published_date,
            })

            if len(results) >= k:
                break

        return results

    def save(self, file_path: Optional[Path | str] = None) -> Path:
        """
        Serialize fitted model artifacts to disk for fast startup.
        """
        if not self._is_fitted:
            raise RuntimeError("Cannot save an unfitted similarity engine.")

        target = Path(file_path) if file_path else (self.config.artifacts_dir / "similarity_engine.joblib")
        target.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "metadata": {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "cases_count": len(self.cases),
                "ngram_range": self.config.ngram_range,
                "max_features": self.config.max_features,
            },
            "cases": [c.to_dict() for c in self.cases],
            "vectorizer": self.vectorizer,
            "tfidf_matrix": self.tfidf_matrix,
        }

        joblib.dump(payload, target, compress=3)
        logger.info("Saved similarity engine artifacts to %s", target)
        return target

    @classmethod
    def load(cls, file_path: Path | str, config: Optional[EngineConfig] = None) -> "ScamPatternSimilarityEngine":
        """
        Load a previously saved engine artifact from disk.
        """
        target = Path(file_path).resolve()
        if not target.exists():
            raise FileNotFoundError(f"Model artifact not found at {target}")

        payload = joblib.load(target)
        engine = cls(config=config)
        engine.cases = [CaseRecord(**c) for c in payload["cases"]]
        engine.vectorizer = payload["vectorizer"]
        engine.tfidf_matrix = payload["tfidf_matrix"]
        engine._is_fitted = True
        logger.info("Loaded similarity engine from %s with %d cases", target, len(engine.cases))
        return engine

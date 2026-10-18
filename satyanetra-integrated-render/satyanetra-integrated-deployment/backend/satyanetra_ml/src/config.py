"""
Configuration module for SatyaNetra ML Engine.
Provides strongly-typed settings with environment variable overrides and sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Tuple


@dataclass(frozen=True)
class EngineConfig:
    """Configuration container for SatyaNetra Scam-Pattern Similarity Engine."""

    # Path to authoritative public cases JSON file
    data_path: Optional[Path] = None

    # NLP Vectorization parameters
    ngram_range: Tuple[int, int] = (1, 2)
    max_features: int = 5000
    sublinear_tf: bool = True
    stop_words: str = "english"
    norm: str = "l2"

    # Inference settings
    default_top_k: int = 5
    similarity_threshold: float = 0.05  # Configurable retrieval cutoff; not a fraud probability
    max_input_length: int = 10000  # Security limit to mitigate DoS / excessive memory use
    min_input_length: int = 3  # Minimum characters required for non-empty input

    # Artifacts storage
    artifacts_dir: Path = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "artifacts"
    )

    def resolve_data_path(self) -> Path:
        """
        Resolve the reference dataset path with graceful fallbacks.
        Order of precedence:
        1. Explicitly configured path in `data_path`
        2. Environment variable `SATYANETRA_DATA_PATH`
        3. Relative path `../data/public_cases.json` (backend repository structure)
        4. Local fallback `data/public_cases.json` (isolated component deployment)
        5. Well-known fallback `C:/satyanetra-backend/data/public_cases.json`
        """
        if self.data_path and Path(self.data_path).exists():
            return Path(self.data_path).resolve()

        env_path = os.getenv("SATYANETRA_DATA_PATH")
        if env_path and Path(env_path).exists():
            return Path(env_path).resolve()

        base_dir = Path(__file__).resolve().parent.parent
        candidates = [
            base_dir.parent / "data" / "public_cases.json",
            base_dir / "data" / "public_cases.json",
            Path("C:/satyanetra-backend/data/public_cases.json"),
        ]

        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()

        # If none exist yet, return standard expected relative path for informative errors
        return (base_dir.parent / "data" / "public_cases.json").resolve()


def get_default_config() -> EngineConfig:
    """Return an immutable default EngineConfig instance."""
    return EngineConfig()

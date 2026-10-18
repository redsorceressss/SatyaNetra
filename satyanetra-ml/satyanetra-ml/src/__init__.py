"""
SatyaNetra ML Engine — Standalone Scam-Pattern Similarity Engine
NLP-based lexical retrieval and explainable risk indicator module.
"""

from .config import EngineConfig, get_default_config
from .data_loader import CaseRecord, load_cases
from .preprocessing import normalize_text, extract_financial_entities
from .model import ScamPatternSimilarityEngine
from .indicators import scan_risk_indicators, RiskIndicatorMatch
from .predict import ScamReportAnalyzer, analyze_report

__all__ = [
    "EngineConfig",
    "get_default_config",
    "CaseRecord",
    "load_cases",
    "normalize_text",
    "extract_financial_entities",
    "ScamPatternSimilarityEngine",
    "scan_risk_indicators",
    "RiskIndicatorMatch",
    "ScamReportAnalyzer",
    "analyze_report",
]

__version__ = "1.0.0"

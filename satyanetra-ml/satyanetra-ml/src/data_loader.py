"""
Data loading and normalization module for SatyaNetra reference public cases.
Reads the curated dataset without coupling to FastAPI, database ORMs, or network services.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import EngineConfig, get_default_config

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaseRecord:
    """Normalized internal representation of a curated reference public case."""

    id: str
    case_title: str
    category: str
    summary: str
    source_url: str
    jurisdiction: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    incident_or_report_date: Optional[str] = None
    amount_value: Optional[float] = None
    amount_currency: Optional[str] = None
    amount_context: Optional[str] = None
    case_status: Optional[str] = None
    status_basis: Optional[str] = None
    source_title: Optional[str] = None
    source_publisher: Optional[str] = None
    source_published_date: Optional[str] = None
    source_type: Optional[str] = None
    last_verified_date: Optional[str] = None

    @property
    def searchable_text(self) -> str:
        """Construct the textual representation used for TF-IDF indexing."""
        parts = [self.case_title, self.category, self.summary]
        if self.amount_context:
            parts.append(self.amount_context)
        return " \n ".join(p.strip() for p in parts if p and p.strip())

    def to_dict(self) -> Dict[str, Any]:
        """Convert record to a clean, JSON-serializable dictionary."""
        return asdict(self)


class DataLoaderError(Exception):
    """Raised when the dataset cannot be loaded or parsed."""
    pass


def parse_case_record(raw: Dict[str, Any], record_idx: int) -> Optional[CaseRecord]:
    """
    Safely validate and normalize a raw dictionary into a CaseRecord.
    Returns None if mandatory identity or text fields are missing.
    """
    if not isinstance(raw, dict):
        logger.warning("Record at index %d is not a JSON object; skipping.", record_idx)
        return None

    case_id = str(raw.get("id", "")).strip()
    case_title = str(raw.get("case_title", "")).strip()
    summary = str(raw.get("summary", "")).strip()

    if not case_id or not case_title or not summary:
        logger.warning(
            "Record at index %d is missing mandatory fields (id, case_title, or summary); skipping.",
            record_idx,
        )
        return None

    # Amount normalization
    raw_amount = raw.get("amount_value")
    amount_value: Optional[float] = None
    if raw_amount is not None:
        try:
            amount_value = float(raw_amount)
        except (ValueError, TypeError):
            logger.debug("Record %s has non-numeric amount_value '%s'", case_id, raw_amount)

    return CaseRecord(
        id=case_id,
        case_title=case_title,
        category=str(raw.get("category", "General Bribery / Corruption")).strip(),
        summary=summary,
        source_url=str(raw.get("source_url", "")).strip(),
        jurisdiction=raw.get("jurisdiction"),
        state=raw.get("state"),
        city=raw.get("city"),
        incident_or_report_date=raw.get("incident_or_report_date"),
        amount_value=amount_value,
        amount_currency=raw.get("amount_currency"),
        amount_context=raw.get("amount_context"),
        case_status=raw.get("case_status"),
        status_basis=raw.get("status_basis"),
        source_title=raw.get("source_title"),
        source_publisher=raw.get("source_publisher"),
        source_published_date=raw.get("source_published_date"),
        source_type=raw.get("source_type"),
        last_verified_date=raw.get("last_verified_date"),
    )


def load_cases(
    path: Optional[Path | str] = None,
    config: Optional[EngineConfig] = None,
    allow_empty: bool = False,
) -> List[CaseRecord]:
    """
    Load and normalize public cases from the designated JSON file.

    Parameters:
    - path: Optional explicit path to public_cases.json.
    - config: Optional EngineConfig instance.
    - allow_empty: If True, returns an empty list instead of raising DataLoaderError
                   when file is missing or empty.

    Returns:
    - List of deduplicated, normalized CaseRecord objects.
    """
    cfg = config or get_default_config()
    target_path = Path(path).resolve() if path else cfg.resolve_data_path()

    if not target_path.exists():
        msg = f"Reference public cases file not found at: {target_path}"
        logger.error(msg)
        if allow_empty:
            return []
        raise DataLoaderError(msg)

    try:
        content = target_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        msg = f"Failed to parse public cases JSON at {target_path}: {exc}"
        logger.error(msg)
        if allow_empty:
            return []
        raise DataLoaderError(msg) from exc
    except OSError as exc:
        msg = f"I/O error reading public cases file at {target_path}: {exc}"
        logger.error(msg)
        if allow_empty:
            return []
        raise DataLoaderError(msg) from exc

    if not isinstance(data, list):
        msg = f"Expected JSON array in {target_path}, but got {type(data).__name__}"
        logger.error(msg)
        if allow_empty:
            return []
        raise DataLoaderError(msg)

    records: List[CaseRecord] = []
    seen_ids = set()

    for idx, item in enumerate(data):
        record = parse_case_record(item, idx)
        if record is None:
            continue
        if record.id in seen_ids:
            logger.warning("Duplicate case ID '%s' found at index %d; skipping duplicate.", record.id, idx)
            continue
        seen_ids.add(record.id)
        records.append(record)

    logger.info("Successfully loaded %d public case records from %s", len(records), target_path)
    return records

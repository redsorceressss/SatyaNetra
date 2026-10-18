"""
Unit tests for SatyaNetra data loading and schema normalization.
"""

import json
from pathlib import Path
import pytest

from src.config import EngineConfig
from src.data_loader import (
    CaseRecord,
    DataLoaderError,
    load_cases,
    parse_case_record,
)


def test_load_authoritative_cases_success():
    """Verify loading from the actual repository public_cases.json dataset."""
    cases = load_cases()
    # Count must match the authoritative backend dataset exactly (no silently dropped records)
    raw = json.loads(EngineConfig().resolve_data_path().read_text(encoding="utf-8"))
    assert len(cases) == len(raw) >= 18
    assert all(isinstance(c, CaseRecord) for c in cases)
    states = {c.state for c in cases}
    assert {"Rajasthan", "Madhya Pradesh", "Louisiana"} <= states


def test_case_record_provenance_and_fields():
    """Verify that case records retain exact provenance, source URLs, and valid IDs."""
    cases = load_cases()
    first_case = cases[0]

    assert first_case.id == "IN-RJ-2025-001"
    assert "Rajasthan ACB" in first_case.case_title
    assert first_case.source_url.startswith("https://")
    assert first_case.status_basis is not None
    assert first_case.searchable_text != ""
    assert first_case.category != ""


def test_missing_file_handling(tmp_path):
    """Verify graceful handling when public_cases.json does not exist."""
    non_existent = tmp_path / "does_not_exist.json"

    # With allow_empty=False, should raise DataLoaderError
    with pytest.raises(DataLoaderError) as exc_info:
        load_cases(path=non_existent, allow_empty=False)
    assert "not found" in str(exc_info.value)

    # With allow_empty=True, should safely return empty list
    empty_res = load_cases(path=non_existent, allow_empty=True)
    assert empty_res == []


def test_malformed_json_handling(tmp_path):
    """Verify graceful handling when file contains invalid JSON."""
    bad_json_file = tmp_path / "bad.json"
    bad_json_file.write_text("{ this is not valid json }", encoding="utf-8")

    with pytest.raises(DataLoaderError) as exc_info:
        load_cases(path=bad_json_file, allow_empty=False)
    assert "Failed to parse" in str(exc_info.value)

    res = load_cases(path=bad_json_file, allow_empty=True)
    assert res == []


def test_non_list_json_handling(tmp_path):
    """Verify graceful handling when JSON root is not an array."""
    dict_file = tmp_path / "dict.json"
    dict_file.write_text(json.dumps({"key": "value"}), encoding="utf-8")

    with pytest.raises(DataLoaderError) as exc_info:
        load_cases(path=dict_file, allow_empty=False)
    assert "Expected JSON array" in str(exc_info.value)


def test_parse_case_record_missing_mandatory_fields():
    """Verify that records missing id, case_title, or summary are discarded."""
    missing_id = {"case_title": "Title", "summary": "Summary"}
    assert parse_case_record(missing_id, 0) is None

    missing_title = {"id": "TEST-01", "summary": "Summary"}
    assert parse_case_record(missing_title, 1) is None

    missing_summary = {"id": "TEST-01", "case_title": "Title"}
    assert parse_case_record(missing_summary, 2) is None


def test_parse_case_record_optional_amount_normalization():
    """Verify robust parsing of numerical and non-numerical amount values."""
    record_dict = {
        "id": "IN-TEST-001",
        "case_title": "Test Title",
        "category": "Test Category",
        "summary": "Test Summary Description",
        "source_url": "https://example.com/source",
        "amount_value": "50000",  # String number
        "amount_currency": "INR",
        "amount_context": "Bribe amount demanded",
    }
    case = parse_case_record(record_dict, 0)
    assert case is not None
    assert case.amount_value == 50000.0

    # Non-numeric string should become None, not crash
    record_dict["amount_value"] = "undisclosed_figure"
    case2 = parse_case_record(record_dict, 1)
    assert case2 is not None
    assert case2.amount_value is None


def test_deduplication_of_records(tmp_path):
    """Verify that duplicate case IDs in source data are safely skipped."""
    dup_file = tmp_path / "duplicates.json"
    data = [
        {"id": "CASE-1", "case_title": "First Case", "summary": "Summary 1"},
        {"id": "CASE-1", "case_title": "Duplicate of First Case", "summary": "Duplicate summary"},
        {"id": "CASE-2", "case_title": "Second Case", "summary": "Summary 2"},
    ]
    dup_file.write_text(json.dumps(data), encoding="utf-8")

    cases = load_cases(path=dup_file)
    assert len(cases) == 2
    assert [c.id for c in cases] == ["CASE-1", "CASE-2"]
    assert cases[0].case_title == "First Case"

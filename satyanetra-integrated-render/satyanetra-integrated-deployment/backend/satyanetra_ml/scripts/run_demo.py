"""
Demonstration script for SatyaNetra Scam-Pattern Similarity Engine.
Runs through multiple synthetic test scenarios covering diverse corruption, extortion,
and non-scam edge cases.

NOTE: All test incident descriptions are SYNTHETIC test inputs designed to evaluate retrieval,
not records of real unverified complaints.
"""

import json
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import load_cases
from src.predict import ScamReportAnalyzer, analyze_report


def print_separator(title: str = "") -> None:
    width = 78
    if title:
        print(f"\n{'=' * 4} {title.upper()} {'=' * (width - len(title) - 6)}")
    else:
        print("=" * width)


def format_demo_case(idx: int, scenario_name: str, input_text: str, result: dict) -> None:
    print_separator(f"Scenario {idx}: {scenario_name}")
    print(f"\n[SYNTHETIC TEST INPUT]:\n\"{input_text}\"\n")
    print(f"Status: {result['status'].upper()} (Input length: {result['input_length']} chars)")
    print(f"Summary: {result['analysis_summary']}")

    # Matched Reference Cases
    print(f"\n--- Matched Reference Cases ({result['matched_cases_count']}) ---")
    if result["similar_cases"]:
        for i, c in enumerate(result["similar_cases"], 1):
            print(f"  {i}. [{c['case_id']}] {c['case_title']}")
            print(f"     Category: {c['category']} | Jurisdiction: {c.get('jurisdiction')} ({c.get('state')})")
            print(f"     Similarity Score: {c['similarity_score']:.4f} (Lexical Retrieval Score)")
            print(f"     Status Basis: {c.get('status_basis', 'N/A')}")
            print(f"     Source Link: {c.get('source_url', 'N/A')}")
            print(f"     Excerpt: {c.get('summary', '')[:120]}...\n")
    else:
        print("  (No reference cases met the similarity threshold)")

    # Risk Indicators
    print(f"--- Detected Risk Indicators ({len(result['risk_indicators'])}) ---")
    if result["risk_indicators"]:
        for i, ind in enumerate(result["risk_indicators"], 1):
            print(f"  {i}. [{ind['severity'].upper()}] {ind['name']} ({ind['code']})")
            print(f"     Explanation: {ind['explanation']}")
            print(f"     Evidence matched: \"{ind['matched_text']}\"")
    else:
        print("  (No specific heuristic risk indicators detected)")

    # Entities
    entities = result.get("detected_entities", {})
    if any(entities.values()):
        print("\n--- Extracted Financial/Contact Clues ---")
        for k, v in entities.items():
            if v:
                print(f"  {k}: {v}")

    # Warnings / Disclaimers
    if result.get("warnings"):
        print(f"\nWarnings: {result['warnings']}")
    print(f"\n[Disclaimer]: {result['disclaimer']}")


def main():
    print("=" * 78)
    print(" SATYANETRA STANDALONE ML ENGINE — INTERACTIVE DEMONSTRATION")
    print("=" * 78)

    # 1. Dataset Loading Verification
    cases = load_cases()
    print(f"\nLoaded {len(cases)} curated reference public cases directly from backend seed data.")
    for c in cases[:3]:
        print(f"  • {c.id}: {c.case_title[:65]}...")
    print(f"  • ... and {len(cases) - 3} more cases.")

    analyzer = ScamReportAnalyzer()

    # 2. Synthetic Test Scenarios
    scenarios = [
        (
            "Electricity Challan Bribery Demand",
            "An electricity distribution staff member in Indore approached me regarding an alleged electricity theft challan. "
            "He demanded ₹30,000 cash under the table to settle the penalty and threatened that power will be disconnected immediately.",
        ),
        (
            "School Recognition Extension Extortion",
            "A block resource education coordinator demanded money to submit a favourable physical verification report for our school's "
            "recognition extension application. He warned the renewal will be stalled unless paid ₹15,000.",
        ),
        (
            "Commercial Driver's License Intermediary Scheme",
            "An intermediary claimed he could obtain an official commercial driver's license without needing to take the required road tests "
            "or training in exchange for an upfront payment of $5,000.",
        ),
        (
            "Coercive 'Digital Arrest' & Credential Phishing",
            "A caller claiming to be from the CBI called stating that an arrest warrant and FIR was registered against my name. "
            "He threatened me with digital arrest and demanded that I share my netbanking OTP and urgently transfer ₹50,000 cash.",
        ),
        (
            "Unrelated Text (Baking Recipe)",
            "To make a lemon drizzle cake, combine self-raising flour, caster sugar, and butter in a large mixing bowl until smooth.",
        ),
        (
            "Invalid / Boundary Inputs (Punctuation & Empty)",
            "?????!!!!!....",
        ),
    ]

    for idx, (name, text) in enumerate(scenarios, 1):
        result = analyzer.analyze_report(text, top_k=3)
        format_demo_case(idx, name, text, result)

    print_separator("DEMONSTRATION COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()

"""
End-to-end unit tests for prediction interface, risk indicators, and JSON serialization.
"""

import json
from src.predict import ScamReportAnalyzer, analyze_report


def test_analyze_report_valid_flow():
    """Verify end-to-end analysis on a realistic bribery incident report."""
    report_text = (
        "An electricity distribution staff member in Indore approached me regarding an electricity theft "
        "notice. He demanded ₹30,000 in cash to settle the challan and threatened that power will be disconnected "
        "if I did not pay immediately."
    )
    result = analyze_report(report_text, top_k=3)

    assert result["status"] == "success"
    assert result["matched_cases_count"] >= 1
    assert result["similar_cases"][0]["case_id"] == "IN-MP-2025-001"
    assert "Electricity-distribution" in result["similar_cases"][0]["case_title"]
    assert result["similar_cases"][0]["similarity_score"] > 0.0

    # Risk indicators should catch urgent transfer and disconnection threat
    indicator_codes = [ind["code"] for ind in result["risk_indicators"]]
    assert "IND_URGENT_TRANSFER" in indicator_codes
    assert "IND_COERCIVE_THREAT" in indicator_codes

    # Entities should detect monetary mention
    assert any("30,000" in m for m in result["detected_entities"]["monetary_mentions"])

    # Verify complete JSON serializability
    serialized = json.dumps(result)
    deserialized = json.loads(serialized)
    assert deserialized["status"] == "success"


def test_analyze_report_empty_and_invalid_inputs():
    """Verify graceful handling of invalid, whitespace-only, and punctuation inputs."""
    # Empty string
    r1 = analyze_report("")
    assert r1["status"] == "invalid_input"
    assert len(r1["warnings"]) > 0

    # Whitespace
    r2 = analyze_report("   \t\n  ")
    assert r2["status"] == "invalid_input"

    # None
    r3 = analyze_report(None)
    assert r3["status"] == "invalid_input"

    # Punctuation only
    r4 = analyze_report("????!!!!!")
    assert r4["status"] == "invalid_input"


def test_analyze_report_unrelated_text():
    """Verify that unrelated text (e.g. cooking recipe) yields no false case matches."""
    text = "To bake a chocolate cake, preheat the oven to 180 degrees and mix flour, cocoa powder, and sugar."
    result = analyze_report(text, threshold=0.1)

    assert result["status"] == "success"
    assert result["matched_cases_count"] == 0
    assert result["similar_cases"] == []
    assert len(result["risk_indicators"]) == 0


def test_risk_indicators_coverage():
    """Verify targeted trigger for each of the 6 defined risk indicator categories."""
    analyzer = ScamReportAnalyzer()

    # 1. Credential Demand
    r_cred = analyzer.analyze_report("He asked me for the bank OTP to verify my profile.")
    codes = [i["code"] for i in r_cred["risk_indicators"]]
    assert "IND_CREDENTIAL_DEMAND" in codes

    # 2. Cautionary advice should NOT trigger credential demand
    r_safe = analyzer.analyze_report("Notice from bank: Do not share your bank OTP with anyone.")
    safe_codes = [i["code"] for i in r_safe["risk_indicators"]]
    assert "IND_CREDENTIAL_DEMAND" not in safe_codes

    # 3. Urgent Transfer
    r_urg = analyzer.analyze_report("You must immediately transfer ₹20,000 cash before it is too late.")
    assert "IND_URGENT_TRANSFER" in [i["code"] for i in r_urg["risk_indicators"]]

    # 4. Authority Impersonation
    r_imp = analyzer.analyze_report("A caller claiming to be from the CBI called regarding an FIR.")
    assert "IND_AUTHORITY_IMPERSONATION" in [i["code"] for i in r_imp["risk_indicators"]]

    # 5. Remote Access
    r_rem = analyzer.analyze_report("He told me to install AnyDesk to clear the error.")
    assert "IND_REMOTE_ACCESS_APP" in [i["code"] for i in r_rem["risk_indicators"]]

    # 6. Coercive Threat / Digital Arrest
    r_thr = analyzer.analyze_report("The officer threatened me with immediate arrest warrant.")
    assert "IND_COERCIVE_THREAT" in [i["code"] for i in r_thr["risk_indicators"]]

    # 7. Unrealistic Gain / Sham Kickback
    r_gain = analyzer.analyze_report("Promised 100% guaranteed returns on trading.")
    assert "IND_UNREALISTIC_GAIN_OR_KICKBACK" in [i["code"] for i in r_gain["risk_indicators"]]


def test_disclaimer_always_present():
    """Verify that the required ethical and legal disclaimer is always provided in the output."""
    res_valid = analyze_report("Officer asked for bribe.")
    assert "disclaimer" in res_valid
    assert "not calibrated fraud probabilities" in res_valid["disclaimer"]

    res_invalid = analyze_report("")
    assert "disclaimer" in res_invalid


def test_new_rajasthan_mp_louisiana_cases_are_retrievable():
    """Each expanded-dataset case should be the top hit for a citizen-style description of it."""
    analyzer = ScamReportAnalyzer()
    probes = {
        "IN-RJ-2026-001": "Court staff and a home guard driver were arrested for taking Rs 40,000 bribe for a favourable court order",
        "IN-RJ-2026-002": "RIICO officials arrested for demanding bribe to allot industrial land plot in Rajasthan",
        "IN-RJ-2025-003": "Jal Jeevan Mission water supply tender contracts rigged with bribes to engineers in Rajasthan",
        "IN-MP-2025-005": "Additional public prosecutor arrested for taking Rs 15,000 bribe in Madhya Pradesh",
        "IN-MP-2026-001": "Legal metrology inspector trapped taking bribe from shopkeeper for weighing scale certificate",
        "IN-MP-2026-002": "Police head constable investigated for disproportionate assets beyond known income",
        "US-LA-2026-002": "Six people pleaded guilty in commercial driver license bribery scheme in Louisiana",
    }
    for expected, text in probes.items():
        result = analyzer.analyze_report(text, top_k=3, threshold=0.0)
        assert result["similar_cases"][0]["case_id"] == expected, expected


def test_indicator_false_positive_and_false_negative_regressions():
    analyzer = ScamReportAnalyzer()

    def codes(text):
        return [i["code"] for i in analyzer.analyze_report(text)["risk_indicators"]]

    # Previously missed
    assert "IND_REMOTE_ACCESS_APP" in codes("I was asked to install an APK file sent on WhatsApp.")
    assert "IND_COERCIVE_THREAT" in codes("Someone threatened that my electricity will be disconnected tonight unless I pay.")
    # Previously a false positive (no money context)
    assert "IND_URGENT_TRANSFER" not in codes("Please send the report immediately after the meeting.")

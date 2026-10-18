"""
Explainable Risk Indicators Module for SatyaNetra.
Provides transparent, rule-based detection of recognized coercive, deceptive, and bribery indicators.

IMPORTANT:
- Risk indicators are heuristic warning signs, NOT proof of fraud or legal guilt.
- No arbitrary numerical fraud probabilities are generated.
- Indicator scanning is decoupled from TF-IDF case retrieval.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RiskIndicatorMatch:
    """Structured representation of a detected warning sign in incident text."""

    code: str
    name: str
    severity: str  # "high", "medium", "low"
    explanation: str
    matched_text: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert match to JSON-serializable dictionary."""
        return asdict(self)


# Precompiled regex patterns for explainable scam & bribery indicators.
# Patterns use boundary and context checks to minimize false positives.

RE_CREDENTIAL_DEMAND = re.compile(
    r"(?i)(?:ask(?:ed|ing)?|demand(?:ed|ing)?|requested|share|send|provide|give|input|enter)\s+"
    r"(?:me\s+for\s+|for\s+)?(?:the\s+|your\s+|my\s+)?(?:bank\s+)?\b"
    r"(?:otp|one[- ]time[- ]password|pin|mpin|cvv|netbanking password|upi pin)\b"
)

RE_CREDENTIAL_CAUTION = re.compile(
    r"(?i)\b(?:never|don'?t|do not|warning:)\s+(?:share|disclose|give)\b"
)

RE_URGENT_TRANSFER = re.compile(
    r"(?i)\b(?:urgently|immediately|right now|within \d+\s*(?:minutes?|hours?)|asap)\b"
    r".{0,40}\b(?:transfer|send|pay|deposit|wire|remit|bribe|challan|cash)\b"
    r"|\b(?:transfer|send|pay|deposit|wire|remit|bribe|challan|cash)\b.{0,40}\b"
    r"(?:urgently|immediately|right now|within \d+\s*(?:minutes?|hours?)|before it is too late)\b"
)

RE_AUTHORITY_IMPERSONATION = re.compile(
    r"(?i)\b(?:claim(?:s|ed|ing)?|pos(?:e|es|ed|ing)|pretend(?:s|ed|ing)?|stated|introduced (?:himself|herself|themselves)|said (?:he|she|they) (?:was|were)|calling from|representing)\b"
    r".{0,35}\b(?:cbi|police|acb|anti[- ]corruption bureau|lokayukta|customs officer|income tax|rbi officer|cyber cell|enforcement directorate|federal agent|doj)\b"
    r"|\b(?:call|notice|warrant)\s+from\s+(?:the\s+)?(?:cbi|police department|cyber crime cell|acb|lokayukta|customs)\b"
)

RE_REMOTE_ACCESS = re.compile(
    r"(?i)\b(?:download|install|run|open|sideload)\b.{0,30}\b"
    r"(?:anydesk|teamviewer|quicksupport|rustdesk|zoho assist|airdroid|apk|remote access app|screen share app)\b"
)

RE_COERCIVE_THREAT = re.compile(
    r"(?i)\b(?:threatened|threat|warning|claimed that)\b.{0,40}\b"
    r"(?:arrest|fir|jail|prosecution|warrant|electricity (?:will be |would be |is going to be )?(?:cut|disconnect\w*)|power cut|sim deactivation|account (?:frozen|block|freeze)|digital arrest)\b"
    r"|\b(?:digital arrest|virtual arrest|arrest warrant|fir registered|(?:power|electricity) (?:will|would) be (?:disconnected|cut off|cut))\b"
)

# Money context required for the urgent-transfer indicator, so generic phrases such as
# "send the report immediately" do not trigger it.
RE_MONEY_CUE = re.compile(
    r"(?i)(?:₹|\brs\.?|\binr\b|\$|\busd\b|\brupees?\b|\bdollars?\b|\blakhs?\b|\bcrores?\b|\d\s*k\b"
    r"|\bmoney\b|\bcash\b|\bamount\b|\bbribe\b|\bfee\b|\bpayment\b|\bfunds?\b|\bchallan\b|\bfine\b|\bpenalty\b|\baccount\b)"
)

RE_UNREALISTIC_GAIN_OR_KICKBACK = re.compile(
    r"(?i)\b(?:100% guaranteed|guaranteed returns?|double your money|risk[- ]free profit|daily profit guaranteed)\b"
    r"|\b(?:sham employment|salary for no work|salary without working|kickback arrangement|kickbacks? disguised)\b"
    r"|\b(?:pay|bribe|money|cash)\b.{0,30}\b(?:for|to secure|in exchange for)\s+(?:a\s+)?(?:government job|appointment|licen[sc]e|tender|contract|challan reduction)\b"
)


def scan_risk_indicators(text: Optional[str]) -> List[RiskIndicatorMatch]:
    """
    Examine incident report text against defined transparent indicator patterns.

    Returns:
    - List of RiskIndicatorMatch objects detailing matched warning signs.
    """
    if not text or not isinstance(text, str):
        return []

    matches: List[RiskIndicatorMatch] = []
    text_sample = text.strip()

    # 1. OTP / Credential Demand
    cred_match = RE_CREDENTIAL_DEMAND.search(text_sample)
    if cred_match:
        # Check if it was merely cautionary advice (e.g., "bank says never share OTP")
        context_window = text_sample[max(0, cred_match.start() - 30):cred_match.end() + 30]
        if not RE_CREDENTIAL_CAUTION.search(context_window):
            matches.append(
                RiskIndicatorMatch(
                    code="IND_CREDENTIAL_DEMAND",
                    name="Credential or OTP Disclosure Demand",
                    severity="high",
                    explanation="Demands or pressure to disclose an OTP, PIN, CVV, or banking password are a strong indicator of unauthorized account compromise attempts.",
                    matched_text=cred_match.group(0),
                )
            )

    # 2. Urgent Money Transfer
    urgent_match = RE_URGENT_TRANSFER.search(text_sample)
    if urgent_match:
        window = text_sample[max(0, urgent_match.start() - 150):urgent_match.end() + 150]
        if not RE_MONEY_CUE.search(window):
            urgent_match = None
    if urgent_match:
        matches.append(
            RiskIndicatorMatch(
                code="IND_URGENT_TRANSFER",
                name="Urgent Money Transfer Demand",
                severity="high",
                explanation="Artificial urgency and demands for rapid financial transfer reduce the opportunity for verification and are typical of coercive fraud.",
                matched_text=urgent_match.group(0),
            )
        )

    # 3. Institutional / Authority Impersonation
    impersonation_match = RE_AUTHORITY_IMPERSONATION.search(text_sample)
    if impersonation_match:
        matches.append(
            RiskIndicatorMatch(
                code="IND_AUTHORITY_IMPERSONATION",
                name="Law Enforcement or Official Impersonation",
                severity="high",
                explanation="Unverified claims of representing law enforcement agencies (CBI, Police, ACB, Cyber Cell) are frequently used to intimidate victims.",
                matched_text=impersonation_match.group(0),
            )
        )

    # 4. Remote Access or Unknown Software
    remote_match = RE_REMOTE_ACCESS.search(text_sample)
    if remote_match:
        matches.append(
            RiskIndicatorMatch(
                code="IND_REMOTE_ACCESS_APP",
                name="Remote Desktop or Unverified Software Installation",
                severity="high",
                explanation="Prompts to install remote-control tools (AnyDesk, TeamViewer) or third-party APKs allow attackers full device and banking app control.",
                matched_text=remote_match.group(0),
            )
        )

    # 5. Coercive Threat / Digital Arrest
    threat_match = RE_COERCIVE_THREAT.search(text_sample)
    if threat_match:
        matches.append(
            RiskIndicatorMatch(
                code="IND_COERCIVE_THREAT",
                name="Threat of Arrest, Account Freeze, or Utility Disconnection",
                severity="high",
                explanation="Threats of imminent arrest, immediate power disconnection, or legal prosecution are coercive tactics used to extort immediate payment.",
                matched_text=threat_match.group(0),
            )
        )

    # 6. Unrealistic Return, Sham Employment, or Kickback
    return_match = RE_UNREALISTIC_GAIN_OR_KICKBACK.search(text_sample)
    if return_match:
        matches.append(
            RiskIndicatorMatch(
                code="IND_UNREALISTIC_GAIN_OR_KICKBACK",
                name="Kickback, Sham Arrangement, or Unrealistic Financial Promise",
                severity="medium",
                explanation="Guaranteed investment returns, sham employment routing, or demands for payments to secure jobs or reduce penalties resemble documented corruption patterns.",
                matched_text=return_match.group(0),
            )
        )

    return matches

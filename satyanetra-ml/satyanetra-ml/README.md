# SatyaNetra Standalone ML Engine

An NLP-based scam-pattern similarity and explainable risk intelligence component for **SatyaNetra** — a financial scam-pattern analysis and anti-corruption intelligence platform.

---

## 1. Executive Summary & Objective

The SatyaNetra ML Engine is designed to analyze suspicious incident descriptions submitted by users or investigators. Given an unstructured report text, the engine:

1. **Preprocesses and normalizes** text while safeguarding important financial tokens, URLs, phone numbers, and scam-related identifiers.
2. **Retrieves and ranks** the most similar curated public reference cases using TF-IDF n-gram vectorization and cosine similarity.
3. **Scans for explainable risk indicators** (such as credential disclosure demands, artificial urgency, institutional impersonation, coercive threats, remote-access apps, and sham kickback arrangements) without arbitrary numerical scoring.
4. **Returns a structured, JSON-serializable diagnostic payload** with full provenance (source links, case IDs, judicial status bases, and legal disclaimers).
5. **Decouples completely from FastAPI and database engines**, enabling standalone execution, automated testing, and zero-downtime microservice or in-process embedding.

---

## 2. Technical Honesty & ML Methodology

### Why TF-IDF and Cosine Similarity?
- **Small Curated Corpus**: The SatyaNetra repository currently contains **12 curated public reference cases** (from Rajasthan and Madhya Pradesh in India, and Louisiana in the United States).
- **Statistical Integrity**: Attempting to train a deep neural network, LLM fine-tune, or supervised binary fraud classifier on 12 reference samples is scientifically unsound and prone to massive overfitting.
- **Retrieval vs. Classification**: In information retrieval, similarity scores quantify **lexical overlap against known reference cases**. They are **retrieval proximity scores, NOT calibrated fraud probabilities or verdicts of guilt**.
- **Transparency & Interpretability**: TF-IDF (unigram + bigram, sublinear TF scaling, L2 normalization) is 100% deterministic, explainable, lightweight (<1 ms inference latency), and does not hallucinate facts.

---

## 3. Dataset Source & Provenance

- **Authoritative Dataset Location**: `data/public_cases.json` in the parent repository.
- **Record Count**: Confirmed **12 curated records** directly from the repository source (not 18; no synthetic or unverified cases have been fabricated).
- **Attribution & Provenance**: Each record includes:
  - Unique Case ID (e.g., `IN-MP-2025-001`, `US-LA-2025-004`)
  - Case Title & Summary
  - Category (e.g., *Utility services / alleged bribery*, *Licensing / bribery*)
  - Official or Media Source URL (e.g., *The Indian Express*, *The Times of India*, *U.S. Department of Justice*)
  - Procedural Case Status & Legal Basis (e.g., *booked_investigation*, *indicted*, *pleaded_guilty_reported*)
  - Reported Financial Amounts and Contextual Explanations

---

## 4. Directory Structure

```text
satyanetra-backend/
└── satyanetra-ml/
    ├── README.md               # Comprehensive system documentation
    ├── requirements.txt        # Core ML and test dependencies
    ├── .gitignore              # Ignores __pycache__, .pytest_cache, virtualenvs
    ├── src/
    │   ├── __init__.py         # Package exports & versioning
    │   ├── config.py           # Engine configuration & multi-location dataset resolution
    │   ├── data_loader.py      # CaseRecord dataclass & graceful JSON data ingestion
    │   ├── preprocessing.py    # Safe text normalization & entity extraction
    │   ├── indicators.py       # Rule-based explainable risk indicators
    │   ├── model.py            # TF-IDF & Cosine Similarity search engine
    │   └── predict.py          # Unified analyze_report facade & JSON output formatting
    ├── tests/
    │   ├── test_data_loader.py    # Schema validation, missing fields, deduplication tests
    │   ├── test_preprocessing.py  # Whitespace, unicode, boundary check tests
    │   ├── test_model.py          # Fit, ranking, top-k, zero-vector, determinism tests
    │   └── test_predict.py        # End-to-end analyzer, indicator coverage, disclaimer tests
    ├── scripts/
    │   ├── run_demo.py         # Multi-scenario interactive terminal demonstration
    │   └── evaluate.py         # IR retrieval benchmark (Hit Rate@K, MRR, latency)
    ├── data/
    │   └── README.md           # Dataset provenance & fallback guidelines
    └── artifacts/
        └── .gitkeep            # Directory for serialized joblib model artifacts
```

---

## 5. Setup & Installation (Windows PowerShell)

The component works with standard Python 3.10+ (tested on Python 3.13).

```powershell
# 1. Navigate to the ML component directory
cd C:\satyanetra-backend\satyanetra-ml

# 2. Activate the virtual environment
..\.venv\Scripts\Activate.ps1

# 3. Verify / install ML dependencies
pip install -r requirements.txt
```

---

## 6. Verification & Execution Commands

### A. Run Automated Unit Test Suite
```powershell
python -m pytest -v
```
*Executes all 25 unit tests covering data loading, preprocessing, similarity ranking, threshold filtering, zero-vector queries, risk indicators, and JSON serialization.*

### B. Run Interactive Demonstration
```powershell
python scripts/run_demo.py
```
*Demonstrates 6 synthetic test scenarios: Electricity challan bribery, School recognition extortion, Commercial driver's license bribery scheme, Coercive "Digital Arrest" with OTP demand, Unrelated text (baking recipe), and Punctuation boundary inputs.*

### C. Run Retrieval Evaluation Benchmark
```powershell
python scripts/evaluate.py
```
*Measures Hit Rate@1, Hit Rate@3, Mean Reciprocal Rank (MRR), and inference latency across documented test probes.*

---

## 7. Explainable Risk Indicators

The engine isolates 6 heuristic risk indicators:

| Indicator Code | Name | Severity | What It Detects |
| :--- | :--- | :---: | :--- |
| `IND_CREDENTIAL_DEMAND` | Credential / OTP Disclosure Demand | HIGH | Pressure to disclose OTP, PIN, CVV, or banking passwords. Filters out cautionary messages. |
| `IND_URGENT_TRANSFER` | Urgent Money Transfer Demand | HIGH | Artificial urgency ("within 15 minutes", "urgently transfer cash") designed to prevent verification. |
| `IND_AUTHORITY_IMPERSONATION` | Law Enforcement / Official Impersonation | HIGH | False claims of representing CBI, Police, ACB, Lokayukta, Cyber Cell, or judicial officers. |
| `IND_REMOTE_ACCESS_APP` | Remote Desktop / Unknown APK | HIGH | Demands to install AnyDesk, TeamViewer, QuickSupport, or sideload third-party APK files. |
| `IND_COERCIVE_THREAT` | Coercive Threat / Digital Arrest | HIGH | Threats of immediate arrest, FIR, electricity disconnection, or account freezing ("digital arrest"). |
| `IND_UNREALISTIC_GAIN_OR_KICKBACK` | Kickback / Sham Job / Guaranteed Return | MEDIUM | Promises of 100% guaranteed investment returns, sham employment payments, or bribes for jobs. |

---

## 8. Proposed Interface for Future FastAPI Backend Integration

When integrating into the existing FastAPI backend (`app/main.py`), the standalone ML engine can be imported directly without any server restructuring:

### Python Interface Contract
```python
from satyanetra_ml.src.predict import analyze_report

result = analyze_report(
    text="Report text entered by citizen...",
    top_k=5,
    threshold=0.05
)
```

### Proposed Endpoint
```python
# In app/main.py:
@app.post("/api/v1/ai/analyze-report", tags=["AI Intelligence"])
def api_analyze_report(payload: ReportAnalysisIn):
    return analyze_report(text=payload.description, top_k=payload.top_k)
```

### JSON Response Structure
```json
{
  "status": "success",
  "input_length": 231,
  "analysis_summary": "Identified 3 similar reference case(s) and detected 3 risk indicator(s) in the report description.",
  "matched_cases_count": 3,
  "similar_cases": [
    {
      "case_id": "IN-MP-2025-001",
      "case_title": "Electricity-distribution employees booked over alleged bribe demand",
      "category": "Utility services / alleged bribery",
      "summary": "Media reported that three electricity-distribution employees were booked...",
      "similarity_score": 0.4030,
      "source_url": "https://timesofindia.indiatimes.com/city/indore/three-discom-employees-in-dhar-booked-on-bribery-charges/amp_articleshow/121420402.cms",
      "jurisdiction": "India",
      "state": "Madhya Pradesh",
      "city": "Indore",
      "case_status": "booked_investigation",
      "status_basis": "Reported case registration and trap; not a conviction",
      "source_publisher": "The Times of India",
      "source_published_date": "2025-05-26"
    }
  ],
  "risk_indicators": [
    {
      "code": "IND_URGENT_TRANSFER",
      "name": "Urgent Money Transfer Demand",
      "severity": "high",
      "explanation": "Artificial urgency and demands for rapid financial transfer reduce the opportunity for verification and are typical of coercive fraud.",
      "matched_text": "urgently transfer ₹50,000 cash"
    }
  ],
  "detected_entities": {
    "urls": [],
    "emails": [],
    "phone_numbers": [],
    "monetary_mentions": ["₹50,000"]
  },
  "warnings": [],
  "disclaimer": "Similarity scores reflect lexical overlap with curated public reference cases and are retrieval scores, not calibrated fraud probabilities. Risk indicators identify heuristic warning patterns for human review and do not constitute legal proof of fraud, guilt, or criminal intent."
}
```

---

## 9. Limitations & Ethical Considerations

1. **Not a Proof of Fraud**: Similarity to a reference case does not mean the user's report is fraudulent or genuine; it simply highlights that similar incidents have been reported publicly.
2. **Presumption of Innocence**: Reference cases distinguish allegations, indictments, and convictions. An allegation is not a finding of guilt.
3. **No Automatic Account Blocking**: This engine provides decision-support and context to investigators and citizens; it must never be used as an automated blocking or profiling mechanism.

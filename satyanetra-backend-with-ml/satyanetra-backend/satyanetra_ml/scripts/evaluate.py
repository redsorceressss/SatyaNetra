"""
Evaluation script for SatyaNetra Scam-Pattern Similarity Engine.
Evaluates information retrieval performance (Hit Rate@K, MRR, latency) on documented
synthetic test probes with verified target cases.

IMPORTANT DATA INTEGRITY & METHODOLOGY NOTE:
The seed dataset contains a small set of curated reference cases (18 at last count). This is a reference collection for
lexical retrieval, NOT a representative training set for a supervised binary fraud classifier.
Attempting to train or report high classifier accuracy on so few cases would be statistically
untenable and intellectually dishonest. This evaluation script strictly measures Information
Retrieval (IR) rank accuracy against curated synthetic test probes.
"""

import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import load_cases
from src.predict import ScamReportAnalyzer


# Synthetic test evaluation probes with verified target ground-truth case IDs
EVALUATION_BENCHMARK: List[Dict[str, str]] = [
    {
        "query_id": "PROBE-01",
        "description": "Electricity department employees demanded ₹30,000 cash to reduce an electricity theft penalty challan.",
        "expected_case_id": "IN-MP-2025-001",
        "category": "Utility services / alleged bribery",
    },
    {
        "query_id": "PROBE-02",
        "description": "A block resource coordinator sought money to approve a favourable physical verification report for school recognition extension.",
        "expected_case_id": "IN-MP-2025-004",
        "category": "Education administration / alleged bribery",
    },
    {
        "query_id": "PROBE-03",
        "description": "Municipal office superintendent arrested by Lokayukta police for bribe demand to reinstate drainage worker.",
        "expected_case_id": "IN-MP-2025-002",
        "category": "Municipal services / alleged bribery",
    },
    {
        "query_id": "PROBE-04",
        "description": "CMHO health department employee caught red-handed accepting money in Jabalpur to release RTI documents.",
        "expected_case_id": "IN-MP-2025-003",
        "category": "Access to information / alleged bribery",
    },
    {
        "query_id": "PROBE-05",
        "description": "Postal worker indicted in federal court for taking bribes to deliver packages containing illicit substances.",
        "expected_case_id": "US-LA-2025-001",
        "category": "Public official bribery",
    },
    {
        "query_id": "PROBE-06",
        "description": "Indictment alleging intermediary accepted $5,000 payments to issue commercial driver's licenses without mandatory testing.",
        "expected_case_id": "US-LA-2025-004",
        "category": "Licensing / bribery",
    },
    {
        "query_id": "PROBE-07",
        "description": "Court employee and a home guard driver arrested for accepting ₹40,000 to arrange a favourable court order in Rajasthan.",
        "expected_case_id": "IN-RJ-2026-001",
        "category": "Judicial administration / alleged bribery",
    },
    {
        "query_id": "PROBE-08",
        "description": "RIICO officials arrested in Rajasthan for taking bribes to allot industrial land plots.",
        "expected_case_id": "IN-RJ-2026-002",
        "category": "Land allotment / alleged bribery",
    },
    {
        "query_id": "PROBE-09",
        "description": "Water supply tender under Jal Jeevan Mission allegedly awarded in exchange for bribes to engineers.",
        "expected_case_id": "IN-RJ-2025-003",
        "category": "Public works procurement / alleged bribery",
    },
    {
        "query_id": "PROBE-10",
        "description": "Additional public prosecutor caught taking ₹15,000 bribe in Madhya Pradesh.",
        "expected_case_id": "IN-MP-2025-005",
        "category": "Legal administration / alleged bribery",
    },
    {
        "query_id": "PROBE-11",
        "description": "Inspector from the legal metrology department trapped accepting a bribe from a shopkeeper.",
        "expected_case_id": "IN-MP-2026-001",
        "category": "Regulatory inspection / alleged bribery",
    },
    {
        "query_id": "PROBE-12",
        "description": "Police head constable under investigation for assets disproportionate to known income.",
        "expected_case_id": "IN-MP-2026-002",
        "category": "Disproportionate assets",
    },
    {
        "query_id": "PROBE-13",
        "description": "Six defendants pleaded guilty in Louisiana in a commercial driver's license bribery scheme.",
        "expected_case_id": "US-LA-2026-002",
        "category": "Licensing / bribery",
    },
]


def run_evaluation() -> None:
    print("=" * 78)
    print(" SATYANETRA RETRIEVAL QUALITY EVALUATION BENCHMARK")
    print("=" * 78)

    cases = load_cases()
    print(f"\n1. DATASET PROFILE:")
    print(f"   • Curated reference public cases: {len(cases)}")
    print(f"   • Evaluation probe queries: {len(EVALUATION_BENCHMARK)}")
    print(f"   • Vectorizer: TF-IDF (unigram + bigram, sublinear TF, L2 norm)")
    print(f"   • Metric: Cosine Similarity Ranking (Top-K)\n")

    analyzer = ScamReportAnalyzer()

    top_1_hits = 0
    top_3_hits = 0
    reciprocal_ranks = []
    latencies = []

    print("-" * 78)
    print(f"{'Probe ID':<10} | {'Expected Case':<15} | {'Rank':<6} | {'Score':<8} | {'Latency':<8}")
    print("-" * 78)

    for probe in EVALUATION_BENCHMARK:
        start_time = time.perf_counter()
        result = analyzer.analyze_report(probe["description"], top_k=5, threshold=0.0)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        latencies.append(elapsed_ms)

        similar_cases = result.get("similar_cases", [])
        expected_id = probe["expected_case_id"]

        rank = -1
        score = 0.0
        for idx, match in enumerate(similar_cases, 1):
            if match["case_id"] == expected_id:
                rank = idx
                score = match["similarity_score"]
                break

        if rank == 1:
            top_1_hits += 1
            top_3_hits += 1
            reciprocal_ranks.append(1.0)
        elif 1 < rank <= 3:
            top_3_hits += 1
            reciprocal_ranks.append(1.0 / rank)
        elif rank > 3:
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

        rank_str = str(rank) if rank > 0 else "MISS"
        score_str = f"{score:.4f}" if rank > 0 else "0.0000"
        print(f"{probe['query_id']:<10} | {expected_id:<15} | {rank_str:<6} | {score_str:<8} | {elapsed_ms:>6.2f}ms")

    total_probes = len(EVALUATION_BENCHMARK)
    hit_rate_top_1 = (top_1_hits / total_probes) * 100
    hit_rate_top_3 = (top_3_hits / total_probes) * 100
    mrr = sum(reciprocal_ranks) / total_probes
    avg_latency = sum(latencies) / total_probes

    print("-" * 78)
    print("\n2. EVALUATION SUMMARY METRICS:")
    print(f"   • Hit Rate @ 1 (Top-1 Match):      {hit_rate_top_1:>6.1f}% ({top_1_hits}/{total_probes})")
    print(f"   • Hit Rate @ 3 (Top-3 Match):      {hit_rate_top_3:>6.1f}% ({top_3_hits}/{total_probes})")
    print(f"   • Mean Reciprocal Rank (MRR):      {mrr:>6.4f}")
    print(f"   • Mean Inference Latency:          {avg_latency:>6.2f} ms")

    print("\n   NOTE: probes are synthetic and were written by the developers with the curated cases in view,")
    print("   so these figures are optimistic upper bounds, not real-world accuracy.")
    print("\n3. METHODOLOGICAL LIMITATIONS & FUTURE ROADMAP:")
    print(f"   • Small Reference Corpus: The current dataset contains {len(cases)} curated cases.")
    print("     This is suitable for retrieval baseline demonstrations but cannot train a supervised")
    print("     classifier. Do not treat retrieval similarity scores as fraud likelihood.")
    print("   • Dataset Expansion Protocol: Future iterations should ingest verified public FIRs, ACB")
    print("     press releases, and judicial orders across more states (UP, Delhi, Bihar, Telangana).")
    print("   • Evaluation Protocol: Ingest a held-out test split of real anonymized citizen reports")
    print("     with human expert relevancy judgments (NDCG@K) before deploying automated routing.")
    print("=" * 78)


if __name__ == "__main__":
    run_evaluation()

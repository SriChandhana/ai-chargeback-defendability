"""
Demo Runner — for the pitch video
------------------------------------
Runs the full pipeline end-to-end and prints output shaped for a
5-minute demo: a few individual dispute cards (score + plain-language
explanation), then the batch-level evaluation numbers.

This is the ONLY script meant to be shown live in the pitch video.
It does not read ground truth for the individual cards — those come
straight from the scorer + LLM layer, exactly as a merchant would see
them. Ground truth is used only in the final "how do we know it works"
section, clearly separated.

Usage: python3 demo/run_batch.py
"""

import json
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from scorer.defendability_scorer import score_all
from llm.explain import explain_dispute, load_reason_map


def print_header(title):
    print()
    print("#" * 70)
    print(f"# {title}")
    print("#" * 70)
    print()


def demo_individual_cases(scored_results, reason_map, n=5):
    """Show a handful of realistic dispute cards, one per score bucket
    where possible — this is what a merchant would actually see."""
    print_header("PART 1: What a merchant sees (individual dispute cards)")

    seen_buckets = set()
    shown = []
    for r in scored_results:
        if r["score_bucket"] not in seen_buckets:
            shown.append(r)
            seen_buckets.add(r["score_bucket"])
        if len(shown) >= n:
            break

    for case in shown:
        explanation, source = explain_dispute(case, reason_map)
        print(f"─── {case['dispute_id']} ───────────────────────────────")
        print(f"Reason code:        {case['reason_code']}")
        print(f"Amount:             ₹{case['dispute_amount']:,}")
        print(f"Response deadline:  {case['response_deadline']}")
        print(f"Defendability:      {case['score']}/100  [{case['score_bucket']}]")
        if case["missing_critical_evidence"]:
            print(f"Missing (critical): {', '.join(case['missing_critical_evidence'])}")
        if case["missing_supporting_evidence"]:
            print(f"Missing (supporting): {', '.join(case['missing_supporting_evidence'])}")
        print(f"\n  \"{explanation}\"")
        print(f"  (explanation source: {source})")
        print()


def demo_batch_summary(scored_results):
    """Aggregate numbers — no LLM, no ground truth, just what the
    scorer produced across all 100 disputes."""
    print_header("PART 2: Batch summary across all disputes (scorer only, no ground truth)")

    total = len(scored_results)
    from collections import Counter
    bucket_counts = Counter(r["score_bucket"] for r in scored_results)

    print(f"Total disputes processed: {total}")
    for bucket in ["HIGH", "MEDIUM", "LOW", "VERY LOW"]:
        count = bucket_counts.get(bucket, 0)
        print(f"  {bucket:10s}: {count:3d}  ({count/total:.0%})")

    total_amount = sum(r["dispute_amount"] for r in scored_results)
    high_amount = sum(r["dispute_amount"] for r in scored_results if r["score_bucket"] == "HIGH")
    very_low_amount = sum(r["dispute_amount"] for r in scored_results if r["score_bucket"] == "VERY LOW")

    print()
    print(f"Total disputed amount in batch: ₹{total_amount:,}")
    print(f"  Amount in HIGH-defendability cases: ₹{high_amount:,}")
    print(f"  Amount in VERY LOW-defendability cases: ₹{very_low_amount:,}")


def demo_evaluation_note():
    """Point to the honest evaluation numbers, run separately, with
    the caveat about what the accuracy figure does and doesn't prove."""
    print_header("PART 3: How do we know the scorer works? (see eval/evaluate.py)")
    print("Run `python3 eval/evaluate.py` for the full breakdown against")
    print("ground truth. Headline honesty note for the pitch:")
    print()
    print("  - Binary accuracy is high on this synthetic set because the")
    print("    ground truth labels and the scorer's pass/fail check share")
    print("    the same underlying rule (any required field missing = not")
    print("    defendable). That confirms the code is bug-free, not that")
    print("    the judgment is sophisticated.")
    print("  - The useful signal is the SCORE DISTRIBUTION within the")
    print("    evidence_gap bucket: scores vary depending on whether the")
    print("    missing field was critical or supporting. This provides")
    print("    more nuance than the binary ground-truth label — though")
    print("    the critical/supporting weighting itself is a designed")
    print("    heuristic, not validated against real-world outcomes.")


def main():
    scored_results = score_all()
    reason_map = load_reason_map()

    demo_individual_cases(scored_results, reason_map, n=5)
    demo_batch_summary(scored_results)
    demo_evaluation_note()


if __name__ == "__main__":
    main()

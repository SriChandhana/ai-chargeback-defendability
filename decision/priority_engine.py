"""
Priority / Action Engine
------------------------
Deterministic rules layer.

Uses ONLY the scorer's output.
No ground truth.
No LLM.

Purpose:
    Convert defendability + urgency + evidence gaps into
    a practical merchant priority and recommended action.
"""
from datetime import datetime
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

# The dataset's dates are fixed to August 2026 and don't move with real
# wall-clock time. Using datetime.now() here would make every dispute
# "overdue" regardless of the actual case, and the demo's output would
# silently change depending on what day you happen to run it. Pinning
# a simulated "now" keeps the demo deterministic and correct against
# the dataset's actual date range (filed dates span 2026-08-01 to
# 2026-08-29 per generate_disputes.py).
SIMULATED_NOW = datetime(2026, 8, 20, 12, 0)


def hours_until_deadline(response_deadline):
    """Return hours remaining until the response deadline, relative to
    the simulated demo clock, not real wall-clock time."""
    deadline = datetime.fromisoformat(response_deadline)
    return (deadline - SIMULATED_NOW).total_seconds() / 3600


def determine_priority(scored_dispute):
    score = scored_dispute["score"]
    missing_critical = scored_dispute["missing_critical_evidence"]

    hours_left = hours_until_deadline(
        scored_dispute["response_deadline"]
    )

    # Deadline already passed — distinct from "urgent but still actionable".
    # Without this check, negative hours_left satisfies every "<= 48" test
    # below and gets misclassified as URGENT alongside genuinely upcoming
    # deadlines, which is misleading in a demo or real use.
    if hours_left < 0:
        return {
            "priority": "OVERDUE",
            "recommended_action": "ESCALATE" if score >= 80 or not missing_critical else "CLOSE — DEADLINE PASSED",
            "reason": "The response deadline has already passed."
        }

    if score >= 80 and hours_left <= 48:
        return {
            "priority": "URGENT",
            "recommended_action": "DEFEND NOW",
            "reason": "High defendability case with a response deadline within 48 hours."
        }

    if score >= 80:
        return {
            "priority": "HIGH",
            "recommended_action": "DEFEND",
            "reason": "Required evidence is present and the case is highly defendable."
        }

    if missing_critical:
        if hours_left <= 48:
            return {
                "priority": "URGENT",
                "recommended_action": "RETRIEVE EVIDENCE",
                "reason": "Critical evidence is missing and the response deadline is within 48 hours."
            }

        return {
            "priority": "HIGH",
            "recommended_action": "RETRIEVE EVIDENCE",
            "reason": "Critical evidence is missing and should be retrieved before submission."
        }

    if score >= 50:
        return {
            "priority": "NORMAL",
            "recommended_action": "REVIEW",
            "reason": "The case has moderate defendability and no critical evidence gap."
        }

    return {
        "priority": "LOW",
        "recommended_action": "REVIEW",
        "reason": "The case currently has low defendability."
    }


def prioritize_all(scored_results):
    results = []
    for dispute in scored_results:
        priority = determine_priority(dispute)
        result = {**dispute, **priority}
        results.append(result)
    return results


def main():
    from scorer.defendability_scorer import score_all
    scored_results = score_all()
    results = prioritize_all(scored_results)
    for result in results[:10]:
        print("=" * 60)
        print(f"{result['dispute_id']} | score={result['score']} ({result['score_bucket']})")
        print(f"Priority: {result['priority']}")
        print(f"Action:   {result['recommended_action']}")
        print(f"Reason:   {result['reason']}")


if __name__ == "__main__":
    main()
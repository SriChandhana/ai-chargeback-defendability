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


def hours_until_deadline(response_deadline):
    """Return hours remaining until the response deadline."""
    deadline = datetime.fromisoformat(response_deadline)
    now = datetime.now()
    return (deadline - now).total_seconds() / 3600


def determine_priority(scored_dispute):
    """
    Determine operational priority from:
      - defendability score
      - response deadline
      - missing critical evidence

    Returns:
      priority
      recommended_action
      reason
    """

    score = scored_dispute["score"]
    missing_critical = scored_dispute["missing_critical_evidence"]

    hours_left = hours_until_deadline(
        scored_dispute["response_deadline"]
    )

    # 1. High-score cases close to deadline:
    #    these are the most valuable cases to act on immediately.
    if score >= 80 and hours_left <= 48:
        return {
            "priority": "URGENT",
            "recommended_action": "DEFEND NOW",
            "reason": "High defendability case with a response deadline within 48 hours."
        }

    # 2. High-score cases with more time:
    if score >= 80:
        return {
            "priority": "HIGH",
            "recommended_action": "DEFEND",
            "reason": "Required evidence is present and the case is highly defendable."
        }

    # 3. Missing critical evidence:
    #    the merchant needs to retrieve evidence before deciding.
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

    # 4. Moderate cases without critical gaps.
    if score >= 50:
        return {
            "priority": "NORMAL",
            "recommended_action": "REVIEW",
            "reason": "The case has moderate defendability and no critical evidence gap."
        }

    # 5. Low-defendability cases.
    return {
        "priority": "LOW",
        "recommended_action": "REVIEW",
        "reason": "The case currently has low defendability."
    }


def prioritize_all(scored_results):
    """Add priority information to every scored dispute."""
    results = []

    for dispute in scored_results:
        priority = determine_priority(dispute)

        result = {
            **dispute,
            **priority,
        }

        results.append(result)

    return results


def main():
    # Import here so this file remains a standalone decision layer.
    from scorer.defendability_scorer import score_all

    scored_results = score_all()
    results = prioritize_all(scored_results)

    for result in results[:10]:
        print("=" * 60)
        print(
            f"{result['dispute_id']} | "
            f"score={result['score']} ({result['score_bucket']})"
        )
        print(f"Priority: {result['priority']}")
        print(f"Action:   {result['recommended_action']}")
        print(f"Reason:   {result['reason']}")


if __name__ == "__main__":
    main()

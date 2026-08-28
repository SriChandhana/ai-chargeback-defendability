"""
Deterministic Defendability Scorer
-----------------------------------
Pure rules engine. No LLM. No ground truth ever passed in here.

Input per dispute: reason_code + the 7 boolean evidence fields.
Output: a score bucket, a numeric score, and the list of missing
required evidence fields (critical vs supporting broken out).

Scoring logic (weighted-proportion formula):
  score = (weighted evidence present / weighted evidence required) * 100

  where each required field contributes:
    - CRITICAL_WEIGHT (2) if it's the reason code's critical evidence
    - SUPPORTING_WEIGHT (1) otherwise

This normalizes correctly regardless of how many required fields a
reason code has — a single-requirement reason code (e.g. UNAUTHORIZED,
one critical field) scores 0 when that field is missing, exactly like
a multi-requirement reason code scores 0 when ALL its fields are missing.
The previous fixed-penalty version (-50 for critical, -20 for supporting)
didn't normalize by total requirement weight, so single-field reason
codes landed at a floor of 50 instead of 0 when their only requirement
was missing. This version fixes that.

Bucket thresholds:
    >= 80  -> HIGH
    50-79  -> MEDIUM
    20-49  -> LOW
    < 20   -> VERY LOW
"""

import json
from pathlib import Path

BASE = Path(__file__).parent.parent / "data"

CRITICAL_WEIGHT = 2
SUPPORTING_WEIGHT = 1


def load_reason_map():
    with open(BASE / "reason_code_evidence_map.json", encoding="utf-8") as f:
        return json.load(f)


def load_disputes():
    with open(BASE / "disputes.json", encoding="utf-8") as f:
        return json.load(f)


def score_bucket(score):
    if score >= 80:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM"
    elif score >= 20:
        return "LOW"
    else:
        return "VERY LOW"


def score_dispute(dispute, reason_map):
    reason_code = dispute["reason_code"]
    rules = reason_map[reason_code]
    required = rules["required_evidence"]
    critical = set(rules["critical_evidence"])

    missing_critical = []
    missing_supporting = []
    weighted_required = 0
    weighted_present = 0

    for field in required:
        weight = CRITICAL_WEIGHT if field in critical else SUPPORTING_WEIGHT
        weighted_required += weight
        if dispute.get(field, False):
            weighted_present += weight
        else:
            if field in critical:
                missing_critical.append(field)
            else:
                missing_supporting.append(field)

    score = round((weighted_present / weighted_required) * 100) if weighted_required else 100
    all_missing = missing_critical + missing_supporting

    return {
        "dispute_id": dispute["dispute_id"],
        "reason_code": reason_code,
        "dispute_amount": dispute["dispute_amount"],
        "response_deadline": dispute["response_deadline"],
        "score": score,
        "score_bucket": score_bucket(score),
        "missing_critical_evidence": missing_critical,
        "missing_supporting_evidence": missing_supporting,
        "all_missing_evidence": all_missing,
        # Convenience flag used downstream (eval + LLM layer):
        # this is the scorer's OWN prediction, not ground truth.
        "predicted_defendable": len(all_missing) == 0,
    }


def score_all():
    reason_map = load_reason_map()
    disputes = load_disputes()
    results = [score_dispute(d, reason_map) for d in disputes]
    return results


def main():
    results = score_all()
    out_path = Path(__file__).parent.parent / "eval" / "scorer_output.json"
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))
    print(f"Scored {len(results)} disputes -> {out_path}")

    # Quick sanity printout, no ground truth involved
    from collections import Counter
    buckets = Counter(r["score_bucket"] for r in results)
    print("Score bucket distribution:", dict(buckets))


if __name__ == "__main__":
    main()

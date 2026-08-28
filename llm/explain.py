"""
LLM Explanation Layer
-----------------------
Takes the DETERMINISTIC scorer's output (score, bucket, missing evidence)
and turns it into a plain-language explanation + recommended next step.

STRICT RULE: this file receives ONLY what defendability_scorer.py produced.
It never sees ground_truth_defendable, ground_truth_missing_evidence, or
the "bucket" label from evaluation_labels.json. The LLM explains a decision
that has already been made deterministically — it does not make the
decision itself. This is the "LLM explains, doesn't decide" principle
from the architecture doc.

Falls back to a template-based explanation if no ANTHROPIC_API_KEY is
set, so the pipeline is runnable and demoable even without API access
(useful during dev, and as a safety net during the live pitch demo).
"""

import json
import os
from pathlib import Path

BASE = Path(__file__).parent.parent

READABLE_FIELD_NAMES = {
    "has_shipping_confirmation": "shipping confirmation",
    "has_tracking_number": "tracking number",
    "has_delivery_proof": "proof of delivery",
    "has_invoice_match": "invoice/amount match",
    "has_customer_communication": "customer communication log",
    "has_auth_otp_log": "authentication/OTP log",
    "has_cancellation_record": "cancellation record",
}


def humanize(field):
    return READABLE_FIELD_NAMES.get(field, field)


def build_prompt(scored_dispute, reason_map):
    reason_code = scored_dispute["reason_code"]
    rules = reason_map[reason_code]
    required = [humanize(f) for f in rules["required_evidence"]]
    missing_critical = [humanize(f) for f in scored_dispute["missing_critical_evidence"]]
    missing_supporting = [humanize(f) for f in scored_dispute["missing_supporting_evidence"]]

    found = [
        humanize(f) for f in rules["required_evidence"]
        if f not in scored_dispute["missing_critical_evidence"]
        and f not in scored_dispute["missing_supporting_evidence"]
    ]

    return f"""You are explaining a chargeback dispute defendability assessment to a merchant.
A deterministic rules engine has ALREADY made the assessment below. Your job is only
to explain it clearly and give a practical next step. Do not second-guess or change
the score or the missing-evidence list — treat them as given facts.

Dispute reason: {reason_code}
Amount: ₹{scored_dispute['dispute_amount']}
Response deadline: {scored_dispute['response_deadline']}

Required evidence for this reason code: {', '.join(required)}
Evidence found: {', '.join(found) if found else 'none'}
Missing (critical): {', '.join(missing_critical) if missing_critical else 'none'}
Missing (supporting): {', '.join(missing_supporting) if missing_supporting else 'none'}

Defendability score: {scored_dispute['score']}/100 ({scored_dispute['score_bucket']})

Write a 2-3 sentence plain-language explanation for the merchant: what the score
means, which missing evidence matters most, and what to do next. Be direct and
practical, not generic."""


def template_fallback(scored_dispute):
    """Deterministic, no-API fallback explanation. Same info, no LLM needed."""
    bucket = scored_dispute["score_bucket"]
    score = scored_dispute["score"]
    critical = scored_dispute["missing_critical_evidence"]
    supporting = scored_dispute["missing_supporting_evidence"]

    strength_word = {
        "HIGH": "strong",
        "MEDIUM": "moderate",
        "LOW": "weak",
        "VERY LOW": "very weak",
    }[bucket]

    if bucket == "HIGH":
        return (f"Your case is strong ({score}/100). All required "
                f"evidence is present — submit your response before the deadline.")
    elif critical:
        names = ", ".join(humanize(f) for f in critical)
        return (f"Your case is {strength_word} ({score}/100). You're missing "
                f"{names}, which is the critical evidence for this dispute type — "
                f"this is the main thing dragging your score down. Retrieve it "
                f"before considering whether to contest.")
    elif supporting:
        names = ", ".join(humanize(f) for f in supporting)
        return (f"Your case is {strength_word} ({score}/100). The critical "
                f"evidence is present, but you're missing {names}. Retrieve this before "
                f"submitting to strengthen your response.")
    else:
        return f"Score: {score}/100 ({bucket})."


def explain_dispute(scored_dispute, reason_map, use_llm=True):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not use_llm or not api_key:
        return template_fallback(scored_dispute), "template_fallback"

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt = build_prompt(scored_dispute, reason_map)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return text.strip(), "llm"
    except Exception as e:
        # Graceful degradation: if the API call fails for any reason
        # (no network, bad key, rate limit), fall back rather than crash.
        return template_fallback(scored_dispute), f"template_fallback (llm_error: {e})"


def load_reason_map():
    with open(BASE / "data" / "reason_code_evidence_map.json", encoding="utf-8") as f:
        return json.load(f)


def load_scorer_output():
    with open(BASE / "eval" / "scorer_output.json", encoding="utf-8") as f:
        return json.load(f)


def main():
    reason_map = load_reason_map()
    scored = load_scorer_output()

    # Demo a handful, not all 100 — this is meant for the pitch video,
    # not a batch job. Pick one from each bucket for variety.
    seen_buckets = set()
    demo_cases = []
    for s in scored:
        if s["score_bucket"] not in seen_buckets:
            demo_cases.append(s)
            seen_buckets.add(s["score_bucket"])
        if len(demo_cases) >= 4:
            break

    for case in demo_cases:
        explanation, source = explain_dispute(case, reason_map)
        print("=" * 60)
        print(f"{case['dispute_id']} | {case['reason_code']} | "
              f"score={case['score']} ({case['score_bucket']}) | source={source}")
        print(explanation)
        print()


if __name__ == "__main__":
    main()


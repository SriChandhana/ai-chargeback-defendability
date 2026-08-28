"""
LLM Explanation Layer
---------------------
Takes ONLY the deterministic scorer output and converts it into
a plain-language explanation + recommended next step.

IMPORTANT:
- The LLM does NOT decide defendability.
- The deterministic scorer already decided the score.
- The LLM only explains that decision.
- Ground truth is NEVER passed to the LLM.

Uses Google Gemini through the google-genai SDK.
Falls back to a deterministic template if:
- GEMINI_API_KEY is missing
- google-genai is not installed
- API call fails
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
    """
    Build the prompt using ONLY scorer output + reason-code requirements.

    Ground truth is intentionally not available here.
    """

    reason_code = scored_dispute["reason_code"]
    rules = reason_map[reason_code]

    required = [
        humanize(field)
        for field in rules["required_evidence"]
    ]

    missing_critical = [
        humanize(field)
        for field in scored_dispute["missing_critical_evidence"]
    ]

    missing_supporting = [
        humanize(field)
        for field in scored_dispute["missing_supporting_evidence"]
    ]

    found = [
        humanize(field)
        for field in rules["required_evidence"]
        if field not in scored_dispute["missing_critical_evidence"]
        and field not in scored_dispute["missing_supporting_evidence"]
    ]

    return f"""
You are explaining a chargeback dispute defendability assessment
to a merchant.

A deterministic rules engine has ALREADY calculated the assessment.

You must NOT change, reinterpret, or second-guess the score.

Your job is ONLY to explain the result clearly and give a practical
next step.

Dispute reason:
{reason_code}

Dispute amount:
₹{scored_dispute["dispute_amount"]}

Response deadline:
{scored_dispute["response_deadline"]}

Required evidence:
{", ".join(required)}

Evidence found:
{", ".join(found) if found else "none"}

Missing critical evidence:
{", ".join(missing_critical) if missing_critical else "none"}

Missing supporting evidence:
{", ".join(missing_supporting) if missing_supporting else "none"}

Defendability score:
{scored_dispute["score"]}/100

Score bucket:
{scored_dispute["score_bucket"]}

Write exactly 2-3 short sentences.

Explain:
1. What the score means.
2. Which missing evidence matters most, if any.
3. What the merchant should do next.

Be direct, practical, and specific.
Do not invent evidence.
Do not invent facts.
Do not change the score.
"""


def template_fallback(scored_dispute):
    """
    Deterministic fallback.
    Works without Gemini.
    """

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
        return (
            f"Your case is strong ({score}/100). "
            "All required evidence is present — submit your response "
            "before the deadline."
        )

    if critical:
        names = ", ".join(
            humanize(field)
            for field in critical
        )

        return (
            f"Your case is {strength_word} ({score}/100). "
            f"You're missing {names}, which is critical evidence "
            "for this dispute type. Retrieve it before deciding "
            "whether to contest."
        )

    if supporting:
        names = ", ".join(
            humanize(field)
            for field in supporting
        )

        return (
            f"Your case is {strength_word} ({score}/100). "
            f"The critical evidence is present, but you're missing "
            f"{names}. Retrieve it before submitting to strengthen "
            "your response."
        )

    return f"Your case has a score of {score}/100 ({bucket})."


def explain_dispute(scored_dispute, reason_map, use_llm=True):

    api_key = os.environ.get("GEMINI_API_KEY")

    # No API key → deterministic fallback
    if not use_llm or not api_key:
        return (
            template_fallback(scored_dispute),
            "template_fallback"
        )

    try:
        from google import genai

        client = genai.Client(
            api_key=api_key
        )

        prompt = build_prompt(
            scored_dispute,
            reason_map
        )

        response = client.models.generate_content(
            model="gemini-3.7-flash",
            contents=prompt,
        )

        text = response.text.strip()

        if not text:
            raise RuntimeError(
                "Gemini returned an empty response"
            )

        return text, "gemini"

    except Exception as e:

        # Never let the LLM failure break the pipeline.
        return (
            template_fallback(scored_dispute),
            f"template_fallback (gemini_error: {e})"
        )


def load_reason_map():

    with open(
        BASE / "data" / "reason_code_evidence_map.json",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def load_scorer_output():

    with open(
        BASE / "eval" / "scorer_output.json",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def main():

    reason_map = load_reason_map()
    scored = load_scorer_output()

    # Pick one case from each score bucket.
    seen_buckets = set()
    demo_cases = []

    for case in scored:

        bucket = case["score_bucket"]

        if bucket not in seen_buckets:

            demo_cases.append(case)
            seen_buckets.add(bucket)

        if len(demo_cases) >= 4:
            break

    for case in demo_cases:

        explanation, source = explain_dispute(
            case,
            reason_map
        )

        print("=" * 60)

        print(
            f"{case['dispute_id']} | "
            f"{case['reason_code']} | "
            f"score={case['score']} "
            f"({case['score_bucket']}) | "
            f"source={source}"
        )

        print(explanation)
        print()


if __name__ == "__main__":
    main()

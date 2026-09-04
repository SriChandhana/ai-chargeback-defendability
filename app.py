import streamlit as st
import json

from scorer.defendability_scorer import score_dispute
from decision.priority_engine import determine_priority
from llm.explain import explain_dispute


# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="Chargeback Defendability",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ Chargeback Defendability")
st.caption(
    "AI Risk Manager — defense-only chargeback evidence assessment"
)


# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------

with open("data/disputes.json", "r") as f:
    disputes = json.load(f)

with open("data/reason_code_evidence_map.json", "r") as f:
    reason_map = json.load(f)

EVIDENCE_LABELS = {
    "has_shipping_confirmation": "Shipping confirmation",
    "has_tracking_number": "Tracking number",
    "has_delivery_proof": "Proof of delivery",
    "has_invoice_match": "Matching invoice",
    "has_customer_communication": "Customer communication",
    "has_auth_otp_log": "Authentication / OTP log",
    "has_cancellation_record": "Cancellation record",
}
# --------------------------------------------------
# DISPUTE SELECTION
# --------------------------------------------------

dispute_ids = [
    dispute["dispute_id"]
    for dispute in disputes
]

selected_id = st.selectbox(
    "Select a dispute",
    dispute_ids
)

dispute = next(
    dispute
    for dispute in disputes
    if dispute["dispute_id"] == selected_id
)


# --------------------------------------------------
# RUN DETERMINISTIC SCORER
# --------------------------------------------------

result = score_dispute(
    dispute,
    reason_map
)


# --------------------------------------------------
# BASIC INFORMATION
# --------------------------------------------------

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Dispute ID",
        result["dispute_id"]
    )

with col2:
    st.metric(
        "Amount",
        f"₹{result['dispute_amount']:,.0f}"
    )

with col3:
    st.metric(
        "Reason Code",
        result["reason_code"]
    )


# --------------------------------------------------
# DEFENDABILITY ASSESSMENT
# --------------------------------------------------

st.divider()

st.subheader("Defendability Assessment")

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Defendability Score",
        f"{result['score']}/100"
    )

with col2:
    st.metric(
        "Risk Level",
        result["score_bucket"]
    )


# --------------------------------------------------
# EVIDENCE STATUS
# --------------------------------------------------

st.subheader("Evidence Status")

missing_critical = result.get(
    "missing_critical_evidence",
    []
)

missing_supporting = result.get(
    "missing_supporting_evidence",
    []
)

if missing_critical:
    st.error(
        "### Critical evidence missing\n\n"
        + "\n".join(
    f"- {EVIDENCE_LABELS.get(evidence, evidence)}"
    for evidence in missing_critical
)
    )
else:
    st.success("No critical evidence missing.")

if missing_supporting:
    st.warning(
        "### Supporting evidence missing\n\n"
        +"\n".join(
    f"- {EVIDENCE_LABELS.get(evidence, evidence)}"
    for evidence in missing_supporting
)
    )
else:
    st.success("No supporting evidence missing.")


# --------------------------------------------------
# PRIORITY / ACTION
# --------------------------------------------------

st.divider()

st.subheader("Decision")

priority = determine_priority(result)

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "Priority",
        priority["priority"]
    )

with col2:
    st.metric(
        "Recommended Action",
        priority["recommended_action"]
    )

st.caption(
    f"Why: {priority['reason']}"
)


# --------------------------------------------------
# AI EXPLANATION
# --------------------------------------------------

st.divider()

st.subheader("AI Explanation")

st.info(
    "Gemini explains the deterministic assessment. "
    "It does not make or change the underlying risk decision."
)

try:
    explanation_text, explanation_source = explain_dispute(
        result,
        reason_map
    )

    st.write(explanation_text)

    st.caption(
        f"Source: {explanation_source}"
    )

except Exception:
    st.warning(
        "AI explanation is currently unavailable."
    )

    st.write(
        f"The dispute has a defendability score of "
        f"{result['score']}/100 and is classified as "
        f"{result['score_bucket']}."
    )
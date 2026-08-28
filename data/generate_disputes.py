import json
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

BASE = Path(__file__).parent

# Keep the reason-code mapping in reason_code_evidence_map.json.
# This generator intentionally keeps ground truth OUT of disputes.json.

ALL_EVIDENCE = [
    "has_shipping_confirmation",
    "has_tracking_number",
    "has_delivery_proof",
    "has_invoice_match",
    "has_customer_communication",
    "has_auth_otp_log",
    "has_cancellation_record",
]

BUCKETS = [
    ("clean_win", 30),
    ("evidence_gap", 30),
    ("unwinnable", 20),
    ("deadline_pressure", 20),
]

with open(BASE / "reason_code_evidence_map.json", encoding="utf-8") as f:
    REASON_MAP = json.load(f)


def make_record(i, bucket):
    reason = random.choice(list(REASON_MAP))
    required = REASON_MAP[reason]["required_evidence"]

    tx_dt = datetime(2026, 8, 1, 9, 0) + timedelta(
        days=random.randint(0, 20),
        hours=random.randint(0, 8),
        minutes=random.choice([0, 15, 30, 45]),
    )

    filed_dt = tx_dt + timedelta(
        days=random.randint(2, 8),
        hours=random.randint(0, 6),
    )

    if bucket == "clean_win":
        evidence = {field: True for field in ALL_EVIDENCE}
        defendable = True
        missing = []

    elif bucket == "evidence_gap":
        evidence = {field: True for field in ALL_EVIDENCE}
        missing = random.sample(
            required, min(random.randint(1, 2), len(required))
        )
        for field in missing:
            evidence[field] = False
        defendable = False

    elif bucket == "unwinnable":
        evidence = {field: False for field in ALL_EVIDENCE}
        defendable = False
        missing = list(required)

    else:
        evidence = {field: True for field in ALL_EVIDENCE}
        defendable = True
        missing = []

    if bucket == "deadline_pressure":
        deadline = filed_dt + timedelta(
            hours=random.choice([6, 12, 18, 24])
        )
    else:
        deadline = filed_dt + timedelta(
            days=random.choice([3, 5, 7])
        )

    record = {
        "dispute_id": f"CB-{i:04d}",
        "reason_code": reason,
        "dispute_amount": random.choice([
            499, 999, 1499, 2499, 4999,
            9999, 19999, 49999, 99999,
        ]),
        "transaction_date": tx_dt.isoformat(timespec="minutes"),
        "dispute_filed_date": filed_dt.isoformat(timespec="minutes"),
        "response_deadline": deadline.isoformat(timespec="minutes"),
        **evidence,
    }

    label = {
        "dispute_id": f"CB-{i:04d}",
        "bucket": bucket,
        "ground_truth_defendable": defendable,
        "ground_truth_missing_evidence": missing,
    }

    return record, label


def generate():
    records = []
    labels = []
    index = 1

    for bucket, count in BUCKETS:
        for _ in range(count):
            record, label = make_record(index, bucket)
            records.append(record)
            labels.append(label)
            index += 1

    random.shuffle(records)

    (BASE / "disputes.json").write_text(
        json.dumps(records, indent=2)
    )
    (BASE / "evaluation_labels.json").write_text(
        json.dumps(labels, indent=2)
    )

    print(f"Generated {len(records)} disputes.")


if __name__ == "__main__":
    generate()

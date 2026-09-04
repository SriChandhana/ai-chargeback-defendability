import json
import random
from datetime import datetime, timedelta
from pathlib import Path

# Different seed from the development dataset.
random.seed(2026)

BASE = Path(__file__).parent

ALL_EVIDENCE = [
    "has_shipping_confirmation",
    "has_tracking_number",
    "has_delivery_proof",
    "has_invoice_match",
    "has_customer_communication",
    "has_auth_otp_log",
    "has_cancellation_record",
]

HELDOUT_BUCKETS = [
    ("clean_win", 12),
    ("evidence_gap", 16),
    ("unwinnable", 8),
    ("deadline_pressure", 4),
]

with open(
    BASE / "reason_code_evidence_map.json",
    encoding="utf-8"
) as f:
    REASON_MAP = json.load(f)


def make_record(i, bucket):
    reason = random.choice(list(REASON_MAP))
    required = REASON_MAP[reason]["required_evidence"]

    tx_dt = datetime(2026, 8, 5, 10, 0) + timedelta(
        days=random.randint(0, 24),
        hours=random.randint(0, 10),
        minutes=random.choice([0, 15, 30, 45]),
    )

    filed_dt = tx_dt + timedelta(
        days=random.randint(1, 9),
        hours=random.randint(0, 8),
    )

    # Construct evidence pattern independently from
    # the original development dataset's random sequence.
    if bucket == "clean_win":
        evidence = {
            field: True
            for field in ALL_EVIDENCE
        }
        defendable = True
        missing = []

    elif bucket == "evidence_gap":
        evidence = {
            field: True
            for field in ALL_EVIDENCE
        }

        missing_count = min(
            random.randint(1, 2),
            len(required)
        )

        missing = random.sample(
            required,
            missing_count
        )

        for field in missing:
            evidence[field] = False

        defendable = False

    elif bucket == "unwinnable":
        evidence = {
            field: False
            for field in ALL_EVIDENCE
        }

        missing = list(required)
        defendable = False

    else:
        evidence = {
            field: True
            for field in ALL_EVIDENCE
        }

        missing = []
        defendable = True

    if bucket == "deadline_pressure":
        deadline = filed_dt + timedelta(
            hours=random.choice([8, 16, 24, 36])
        )
    else:
        deadline = filed_dt + timedelta(
            days=random.choice([2, 4, 6, 8])
        )

    dispute_id = f"HO-{i:04d}"

    record = {
        "dispute_id": dispute_id,
        "reason_code": reason,
        "dispute_amount": random.choice([
            799,
            1299,
            1999,
            2999,
            5999,
            12999,
            24999,
            74999,
        ]),
        "transaction_date": tx_dt.isoformat(
            timespec="minutes"
        ),
        "dispute_filed_date": filed_dt.isoformat(
            timespec="minutes"
        ),
        "response_deadline": deadline.isoformat(
            timespec="minutes"
        ),
        **evidence,
    }

    label = {
        "dispute_id": dispute_id,
        "bucket": bucket,
        "ground_truth_defendable": defendable,
        "ground_truth_missing_evidence": missing,
    }

    return record, label


def generate():
    records = []
    labels = []

    index = 1

    for bucket, count in HELDOUT_BUCKETS:
        for _ in range(count):
            record, label = make_record(
                index,
                bucket
            )

            records.append(record)
            labels.append(label)

            index += 1

    # Shuffle records only.
    # Labels retain their dispute IDs and are matched by ID.
    random.shuffle(records)

    (BASE / "heldout_disputes.json").write_text(
        json.dumps(records, indent=2)
    )

    (BASE / "heldout_labels.json").write_text(
        json.dumps(labels, indent=2)
    )

    print(
        f"Generated {len(records)} held-out disputes."
    )


if __name__ == "__main__":
    generate()
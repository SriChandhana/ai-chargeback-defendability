import json
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE))

from scorer.defendability_scorer import score_dispute

def precision(tp, fp):
    return tp / (tp + fp) if (tp + fp) else 0.0


def recall(tp, fn):
    return tp / (tp + fn) if (tp + fn) else 0.0


def f1(p, r):
    return 2 * p * r / (p + r) if (p + r) else 0.0


def main():
    with open(BASE / "data" / "heldout_disputes.json") as f:
        disputes = json.load(f)

    with open(BASE / "data" / "heldout_labels.json") as f:
        labels = json.load(f)

    with open(BASE / "data" / "reason_code_evidence_map.json") as f:
        reason_map = json.load(f)

    labels_by_id = {
        label["dispute_id"]: label
        for label in labels
    }

    tp = fp = tn = fn = 0

    evidence_tp = 0
    evidence_fp = 0
    evidence_fn = 0

    bucket_results = {}

    for dispute in disputes:
        result = score_dispute(dispute, reason_map)
        label = labels_by_id[dispute["dispute_id"]]

        predicted = result["predicted_defendable"]
        actual = label["ground_truth_defendable"]

        if predicted and actual:
            tp += 1
        elif predicted and not actual:
            fp += 1
        elif not predicted and actual:
            fn += 1
        else:
            tn += 1

        predicted_missing = set(
            result["all_missing_evidence"]
        )

        true_missing = set(
            label["ground_truth_missing_evidence"]
        )

        evidence_tp += len(
            predicted_missing & true_missing
        )

        evidence_fp += len(
            predicted_missing - true_missing
        )

        evidence_fn += len(
            true_missing - predicted_missing
        )

        bucket = label["bucket"]

        if bucket not in bucket_results:
            bucket_results[bucket] = {
                "count": 0,
                "tp": 0,
                "fp": 0,
                "tn": 0,
                "fn": 0,
            }

        bucket_results[bucket]["count"] += 1

        if predicted and actual:
            bucket_results[bucket]["tp"] += 1
        elif predicted and not actual:
            bucket_results[bucket]["fp"] += 1
        elif not predicted and actual:
            bucket_results[bucket]["fn"] += 1
        else:
            bucket_results[bucket]["tn"] += 1

    total = len(disputes)

    accuracy = (tp + tn) / total if total else 0

    p = precision(tp, fp)
    r = recall(tp, fn)
    binary_f1 = f1(p, r)

    evidence_precision = precision(
        evidence_tp,
        evidence_fp
    )

    evidence_recall = recall(
        evidence_tp,
        evidence_fn
    )

    evidence_f1 = f1(
        evidence_precision,
        evidence_recall
    )

    print("=" * 60)
    print("HELD-OUT EVALUATION")
    print("=" * 60)

    print(f"Total disputes evaluated: {total}")
    print(f"Accuracy: {accuracy * 100:.1f}%")
    print(f"Precision: {p * 100:.1f}%")
    print(f"Recall: {r * 100:.1f}%")
    print(f"F1: {binary_f1 * 100:.1f}%")

    print()
    print("CONFUSION MATRIX")
    print(f"TP: {tp}")
    print(f"FP: {fp}")
    print(f"TN: {tn}")
    print(f"FN: {fn}")

    print()
    print("EVIDENCE-GAP DETECTION")
    print(
        f"Precision: "
        f"{evidence_precision * 100:.1f}%"
    )
    print(
        f"Recall: "
        f"{evidence_recall * 100:.1f}%"
    )
    print(
        f"F1: "
        f"{evidence_f1 * 100:.1f}%"
    )
    print(f"TP: {evidence_tp}")
    print(f"FP: {evidence_fp}")
    print(f"FN: {evidence_fn}")

    print()
    print("BY SCENARIO")

    for bucket, stats in bucket_results.items():
        print(
            f"{bucket}: "
            f"{stats['count']} cases | "
            f"TP={stats['tp']} "
            f"FP={stats['fp']} "
            f"TN={stats['tn']} "
            f"FN={stats['fn']}"
        )


if __name__ == "__main__":
    main()
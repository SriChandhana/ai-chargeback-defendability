"""
Evaluation Script
------------------
The ONLY file in this repo that reads evaluation_labels.json.
Joins the scorer's independent predictions to ground truth by dispute_id
and reports honest metrics: accuracy, precision/recall on the
"defendable" call, and evidence-gap detection precision/recall,
broken down by bucket.
"""

import json
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).parent.parent


def load_scorer_output():
    with open(BASE / "eval" / "scorer_output.json", encoding="utf-8") as f:
        return {r["dispute_id"]: r for r in json.load(f)}


def load_labels():
    with open(BASE / "data" / "evaluation_labels.json", encoding="utf-8") as f:
        return {l["dispute_id"]: l for l in json.load(f)}


def evaluate():
    scored = load_scorer_output()
    labels = load_labels()

    assert set(scored) == set(labels), "Mismatch between scored disputes and labels"

    tp = fp = tn = fn = 0
    by_bucket = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0, "total": 0})

    evidence_tp = evidence_fp = evidence_fn = 0

    mismatches = []

    for did, label in labels.items():
        pred = scored[did]["predicted_defendable"]
        actual = label["ground_truth_defendable"]
        bucket = label["bucket"]
        by_bucket[bucket]["total"] += 1

        if pred and actual:
            tp += 1
            by_bucket[bucket]["tp"] += 1
        elif pred and not actual:
            fp += 1
            by_bucket[bucket]["fp"] += 1
            mismatches.append((did, bucket, "predicted DEFENDABLE, actually NOT — costly false positive"))
        elif not pred and actual:
            fn += 1
            by_bucket[bucket]["fn"] += 1
            mismatches.append((did, bucket, "predicted NOT defendable, actually WAS — missed a winnable case"))
        else:
            tn += 1
            by_bucket[bucket]["tn"] += 1

        # Evidence-gap detection: does predicted missing-evidence set match ground truth?
        pred_missing = set(scored[did]["all_missing_evidence"])
        true_missing = set(label["ground_truth_missing_evidence"])
        if pred_missing == true_missing:
            evidence_tp += 1
        elif pred_missing - true_missing:
            evidence_fp += 1
        elif true_missing - pred_missing:
            evidence_fn += 1

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0

    print("=" * 60)
    print("DEFENDABILITY CLASSIFICATION (predicted vs ground truth)")
    print("=" * 60)
    print(f"Total disputes evaluated: {total}")
    print(f"Accuracy:  {accuracy:.1%}")
    print(f"Precision: {precision:.1%}  (of cases we called defendable, how many really were)")
    print(f"Recall:    {recall:.1%}  (of truly defendable cases, how many we caught)")
    print(f"True Positives:  {tp}")
    print(f"False Positives: {fp}  <- costly: told merchant to fight a losing case")
    print(f"True Negatives:  {tn}")
    print(f"False Negatives: {fn}  <- costly: told merchant not to fight a winnable case")
    print()
    print("BY BUCKET:")
    for bucket, stats in by_bucket.items():
        print(f"  {bucket:20s} total={stats['total']:3d}  "
              f"tp={stats['tp']:3d} fp={stats['fp']:3d} "
              f"tn={stats['tn']:3d} fn={stats['fn']:3d}")
    print()
    print("EVIDENCE-GAP DETECTION (exact match on missing-field set)")
    ev_total = evidence_tp + evidence_fp + evidence_fn
    print(f"Exact match: {evidence_tp}/{ev_total} disputes "
          f"({evidence_tp/ev_total:.1%})" if ev_total else "N/A")
    print()
    if mismatches:
        print(f"MISMATCHES ({len(mismatches)}) — for your 'what broke' section:")
        for did, bucket, reason in mismatches[:20]:
            print(f"  {did} [{bucket}]: {reason}")
        if len(mismatches) > 20:
            print(f"  ... and {len(mismatches) - 20} more")

    print()
    print("=" * 60)
    print("SCORE DISTRIBUTION WITHIN EACH BUCKET (the real nuance)")
    print("=" * 60)
    print("Binary accuracy above hides this: within evidence_gap cases,")
    print("losing a CRITICAL field vs a SUPPORTING field should produce")
    print("very different scores even though both are 'not defendable'.")
    print()
    bucket_scores = defaultdict(list)
    for did, label in labels.items():
        bucket_scores[label["bucket"]].append(scored[did]["score"])

    for bucket in ["clean_win", "evidence_gap", "unwinnable", "deadline_pressure"]:
        scores = sorted(bucket_scores[bucket])
        if not scores:
            continue
        dist = defaultdict(int)
        for s in scores:
            dist[scored_bucket_label(s)] += 1
        print(f"  {bucket:20s} min={min(scores):3d} max={max(scores):3d} "
              f"avg={sum(scores)/len(scores):5.1f}  "
              f"dist={dict(dist)}")


def scored_bucket_label(score):
    if score >= 80:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM"
    elif score >= 20:
        return "LOW"
    else:
        return "VERY LOW"


if __name__ == "__main__":
    evaluate()


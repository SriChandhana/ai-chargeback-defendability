# Evaluation Report

## 1. Objective

The system evaluates whether a merchant has sufficient evidence to defend a
chargeback dispute.

The evaluation measures:

- Defendability classification
- Missing-evidence detection
- Performance by dispute bucket
- Performance by reason code
- Distribution of the continuous defendability score

The evaluation layer is completely separated from the production decision
logic. The deterministic scorer never reads ground-truth labels.

---

## 2. Evaluation Dataset

The current evaluation uses 100 synthetic chargeback disputes.

Each dispute contains:

- `dispute_id`
- `reason_code`
- `dispute_amount`
- `response_deadline`
- Evidence availability fields

Ground-truth labels are stored separately in:

`data/evaluation_labels.json`

The scorer operates only on:

`data/disputes.json`

This separation prevents the scorer from accessing evaluation labels while
making a decision.

---

## 3. Defendability Classification

The deterministic scorer produces:

- A numeric defendability score from 0–100
- A score bucket:
  - HIGH
  - MEDIUM
  - LOW
  - VERY LOW
- Missing critical evidence
- Missing supporting evidence
- A binary `predicted_defendable` decision

Current evaluation:

| Metric | Result |
|---|---:|
| Disputes evaluated | 100 |
| Accuracy | 100.0% |
| Precision | 100.0% |
| Recall | 100.0% |
| False positives | 0 |
| False negatives | 0 |

### Bucket breakdown

| Bucket | Total | TP | FP | TN | FN |
|---|---:|---:|---:|---:|---:|
| clean_win | 30 | 30 | 0 | 0 | 0 |
| evidence_gap | 30 | 0 | 0 | 30 | 0 |
| unwinnable | 20 | 0 | 0 | 20 | 0 |
| deadline_pressure | 20 | 20 | 0 | 0 | 0 |

---

## 4. Evidence-Gap Detection

Missing evidence is evaluated at the individual-field level rather than
treating an entire dispute as one prediction.

For every dispute:

- True positive = a field correctly identified as missing
- False positive = a field incorrectly identified as missing
- False negative = a genuinely missing field that was not detected

Current results:

| Metric | Result |
|---|---:|
| Precision | 100.0% |
| Recall | 100.0% |
| F1 | 100.0% |
| True positives | 75 |
| False positives | 0 |
| False negatives | 0 |

---

## 5. Score Distribution

Binary classification hides an important distinction: two disputes can both be
classified as "not defendable" while having very different evidence positions.

The weighted scorer therefore produces a continuous score.

| Bucket | Min | Max | Average |
|---|---:|---:|---:|
| clean_win | 100 | 100 | 100.0 |
| evidence_gap | 0 | 75 | 26.4 |
| unwinnable | 0 | 0 | 0.0 |
| deadline_pressure | 100 | 100 | 100.0 |

The `evidence_gap` cases demonstrate the intended behavior of the weighted
scoring system: missing critical evidence can reduce the score substantially
more than missing supporting evidence.

---

## 6. Reason-Code Analysis

Performance is also reported by reason code in `evaluate.py`.

This allows us to identify whether the evidence rules behave consistently
across different classes of chargebacks rather than relying only on an
aggregate metric.

---

## 7. Important Evaluation Limitation

The current 100% classification metrics must **not** be interpreted as
evidence that the system achieves 100% real-world chargeback prediction
accuracy.

The current synthetic ground-truth labels were generated using the same
underlying evidence-completeness rule implemented by the deterministic
scorer.

Therefore, these results primarily demonstrate:

1. The scorer correctly implements the defined evidence rules.
2. The evaluation pipeline correctly joins predictions to labels.
3. Missing-evidence detection is internally consistent.
4. The weighted scoring system produces differentiated scores.

They do **not** establish real-world win probability or actual chargeback
outcomes.

A real-world evaluation would require independently labeled historical
chargebacks and their eventual outcomes.

---

## 8. False-Positive Consideration

For a defense-only system, a false positive is particularly important:

> The system recommends defending a dispute that ultimately should not have
> been defended.

The current synthetic evaluation contains zero false positives.

However, because the labels are generated from the same evidence rule as the
scorer, this should be treated as a pipeline validation result rather than a
claim of zero real-world false-positive risk.

Future evaluation should measure the financial cost associated with incorrect
defense recommendations using independently labeled historical disputes.

---

## 9. Current Score Distribution

Across the 100 disputes:

- HIGH: 50
- MEDIUM: 10
- LOW: 6
- VERY LOW: 34

The system therefore provides more information than a simple binary
"fight / don't fight" classifier.

It identifies:

- cases with complete evidence,
- cases with partial evidence,
- cases with critical evidence gaps,
- and cases with effectively no required evidence.

---

## 10. Evaluation Architecture

```text
                    ┌──────────────────────┐
                    │   disputes.json      │
                    │  (no ground truth)   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Deterministic Scorer │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ scorer_output.json   │
                    └──────────┬───────────┘
                               │
                               │
          ┌────────────────────┘
          │
          ▼
┌──────────────────────────────┐
│ evaluation_labels.json       │
│ (evaluation only)            │
└──────────────┬───────────────┘
               │
               ▼
      ┌───────────────────┐
      │  evaluate.py      │
      └─────────┬─────────┘
                │
                ▼
      Metrics + breakdowns

**# 🛡️ Chargeback Defendability**

**\*\*Razorpay AI Buildathon 2026 — Track 02: AI Risk Manager\*\***

A defense-only AI risk manager that helps merchants assess whether a chargeback is sufficiently supported by evidence, identify missing evidence, prioritize cases, and understand what action to take — with a deterministic decision engine and an LLM that explains, but never decides.

\---

**## Problem**

Chargeback handling is not only about detecting fraud. Merchants also receive disputes related to delivery, subscriptions, duplicate charges, authorization, and product/service issues.

A merchant typically has a limited response window to contest a dispute. The challenge is to quickly answer:

\- How defendable is this dispute?

\- What evidence is missing?

\- Which missing evidence is critical, and which is merely supporting?

\- Which cases should be handled first, given deadlines?

\- Why did the system reach this decision?

The goal is to turn a raw dispute record into a clear, actionable evidence-recovery decision — fast enough to matter before the deadline.

\---

**## Solution**

**\*\*Chargeback Defendability\*\*** is a defense-only decision-support system that evaluates the evidence available for each dispute.

The system:

1\. Maps the dispute reason code to the evidence required to defend it.

2\. Calculates a deterministic defendability score.

3\. Identifies critical and supporting evidence gaps.

4\. Converts the assessment and deadline into an operational priority and recommended action.

5\. Uses **\*\*Gemini\*\*** to explain the deterministic decision in merchant-friendly language.

The LLM is deliberately kept out of the underlying risk decision. It explains the result the deterministic system already produced — it does not change it.

\---

**## How It Works**

**### 1. Evidence Mapping**

Each chargeback reason code is mapped to the evidence required to support a defense:

\- Shipping confirmation

\- Tracking number

\- Proof of delivery

\- Matching invoice

\- Customer communication

\- Authentication / OTP log

\- Cancellation record

Evidence is classified as **\*\*critical\*\*** or **\*\*supporting\*\*** depending on the dispute type — e.g. proof of delivery is critical for \`ITEM\_NOT\_RECEIVED\`, while tracking number is only supporting.

**### 2. Defendability Scoring**

The scorer calculates a weighted evidence-completeness score:

\- Critical evidence weight: **\*\*2\*\***

\- Supporting evidence weight: **\*\*1\*\***

\`\`\`text

              weighted evidence present

score  =    ──────────────────────────── × 100

              weighted evidence required

\`\`\`

Normalizing by total required weight — rather than applying a fixed penalty per missing field — ensures reason codes with only one required field (e.g. \`UNAUTHORIZED\`) score a true 0 when that evidence is absent, instead of bottoming out at an artificial floor.

**\*\*Score buckets:\*\***

\| Score | Bucket |

\|---:|---|

\| 80–100 | HIGH |

\| 50–79 | MEDIUM |

\| 20–49 | LOW |

\| 0–19 | VERY LOW |

A dispute is predicted-defendable when all required evidence is present.

**### 3. Evidence-Gap Detection**

The scorer separately reports:

\- Missing critical evidence

\- Missing supporting evidence

\- All missing evidence

\`\`\`text

Defendability: 0/100

Critical evidence missing:

\- Cancellation record

Supporting evidence missing:

\- Matching invoice

\`\`\`

This makes the output actionable — not just a score, but a specific to-do list.

**### 4. Priority / Action Engine**

The deterministic priority engine combines:

\- Defendability score

\- Missing critical evidence

\- Response deadline

...into a priority, a recommended action, and a plain-language reason:

\`\`\`text

URGENT   → DEFEND NOW              (high score, deadline ≤48h)

HIGH     → DEFEND                  (high score, more time)

URGENT   → RETRIEVE EVIDENCE       (critical gap, deadline ≤48h)

HIGH     → RETRIEVE EVIDENCE       (critical gap, more time)

NORMAL   → REVIEW                  (moderate score, no critical gap)

LOW      → REVIEW                  (low score)

OVERDUE  → ESCALATE / CLOSE        (deadline already passed)

\`\`\`

The demo uses a **\*\*fixed simulated clock\*\*** rather than real wall-clock time, since the synthetic dataset's dates are fixed to August 2026. Without this, every dispute would eventually read as impossibly overdue depending on when the demo happens to run — pinning the clock keeps priority output deterministic and correct against the dataset's actual date range.

**### 5. Gemini Explanation**

Gemini receives the deterministic assessment — reason code, dispute amount, response deadline, defendability score, and missing evidence — and turns it into a concise, merchant-facing explanation.

It does **\*\*not\*\*** receive evaluation ground truth, and it does not determine the score, the evidence gaps, or the priority. If Gemini is unavailable, the app falls back to a deterministic template explanation so the demo never breaks.

\---

**## Architecture**

\`\`\`text

                    disputes.json

                         │

                         ▼

              ┌──────────────────────┐

              │   Evidence Mapping   │

              │  Reason Code  ──►    │

              │  Required Evidence   │

              └──────────┬───────────┘

                         │

                         ▼

              ┌──────────────────────┐

              │ Defendability Scorer │

              │  Weighted Evidence   │

              │ Completeness Score   │

              └──────────┬───────────┘

                         │

              ┌──────────┴───────────┐

              ▼                      ▼

       Evidence Gaps          Score / Bucket

              │                      │

              └──────────┬───────────┘

                         ▼

              ┌──────────────────────┐

              │  Priority / Action   │

              │       Engine         │

              │ Score + Deadline +   │

              │  Critical Evidence   │

              └──────────┬───────────┘

                         ▼

              ┌──────────────────────┐

              │  Gemini Explanation  │

              │ Explains, does NOT   │

              │       decide         │

              └──────────┬───────────┘

                         ▼

              ┌──────────────────────┐

              │   Streamlit Demo UI  │

              └──────────────────────┘

\`\`\`

Evaluation is kept structurally separate from the merchant-facing pipeline — the scorer never sees ground truth:

\`\`\`text

evaluation\_labels.json

        │

        ▼

    evaluate.py

        │

        ▼

Precision / Recall / F1

\`\`\`

\---

**## Evaluation**

The current prototype uses **\*\*100 synthetic dispute records\*\***, generated with controlled scenario distributions to evaluate the scoring and evidence-gap logic.

\| Scenario | Cases |

\|---|---:|

\| Clean win | 30 |

\| Evidence gap | 30 |

\| Unwinnable | 20 |

\| Deadline pressure | 20 |

**\*\*Results:\*\***

\| Metric | Result |

\|---|---:|

\| Disputes evaluated | 100 |

\| Accuracy | 100% |

\| Precision | 100% |

\| Recall | 100% |

\| Evidence-gap Precision | 100% |

\| Evidence-gap Recall | 100% |

\| Evidence-gap F1 | 100% |

\| False Positives | 0 |

\| False Negatives | 0 |

Full breakdown available in [\`eval/EVALUATION\_REPORT.md\`]\(eval/EVALUATION\_REPORT.md).

**### Held-Out Synthetic Evaluation**

A separate 40-dispute test set was generated independently using a different random seed and scenario distribution. These records were not used during scorer development.

| Metric | Held-out result |
|---|---:|
| Disputes evaluated | 40 |
| Accuracy | 100% |
| Precision | 100% |
| Recall | 100% |
| F1 | 100% |
| Evidence-gap Precision | 100% |
| Evidence-gap Recall | 100% |
| Evidence-gap F1 | 100% |
| False Positives | 0 |
| False Negatives | 0 |

**Held-out scenario distribution:**

| Scenario | Cases |
|---|---:|
| Clean win | 12 |
| Evidence gap | 16 |
| Unwinnable | 8 |
| Deadline pressure | 4 |

The held-out run confirms that the deterministic scorer reproduces the designed evidence-completeness rule on separately generated synthetic cases. It should not be interpreted as real-world predictive accuracy because the held-out labels are still synthetic and derived from controlled evidence patterns.

Run it with:

```bash
python eval/evaluate_heldout.py
```

**### Important Limitation**

These 100% metrics should **\*\*not\*\*** be read as real-world predictive accuracy.

The original synthetic ground-truth labels were generated from the same evidence-completeness rule the deterministic scorer checks. The separate 40-case held-out set uses a different seed and scenario distribution, but its labels are also synthetic and derived from controlled evidence patterns. Therefore, both evaluations primarily validate implementation consistency and synthetic generalization — not real-world judgment quality.

The critical-vs-supporting evidence weighting is a designed heuristic and has not been validated against real historical chargeback outcomes. A stronger future evaluation would use an independently labeled dataset or real dispute resolution history.

\---

**## Build Challenges & What Broke**

Real issues hit and fixed during development — not invented for the pitch:

**\*\*Field-name mismatches.\*\*** The evidence-requirement map initially referenced fields (\`product\_listing\_snapshot\`, \`device\_ip\_match\`, \`mandate\_log\`) that didn't exist anywhere in the actual dataset schema, which only has seven real evidence fields (\`has\_shipping\_confirmation\`, \`has\_tracking\_number\`, \`has\_delivery\_proof\`, \`has\_invoice\_match\`, \`has\_customer\_communication\`, \`has\_auth\_otp\_log\`, \`has\_cancellation\_record\`). Caught before the scorer was built on top of it, and the map was corrected to reference only real fields.

**\*\*Fixed-penalty scoring produced an illogical floor.\*\*** An early scoring version applied a flat -50 penalty for a missing critical field and -20 for supporting, regardless of how many total fields a reason code required. This meant a reason code with only one required field (e.g. \`UNAUTHORIZED\`) landed at 50/100 when its only piece of evidence was completely absent — the same score band as a partially-defensible case. Fixed by switching to weighted evidence completeness (\`present / required × 100\`), so single-requirement reason codes correctly bottom out at 0.

**\*\*Evidence-gap evaluation counted per-dispute instead of per-field.\*\*** The first evaluation script used an \`if/elif\` chain that could only register a dispute as an evidence-gap false positive *\*or\** false negative, never both — so a dispute with one correctly-flagged gap and one incorrectly-flagged gap would silently lose one of those signals. Rewritten to compare predicted vs. true missing-evidence sets at the individual field level using set arithmetic (\`TP = predicted ∩ true\`, \`FP = predicted - true\`, \`FN = true - predicted\`).

**\*\*Deadline logic broke against real wall-clock time.\*\*** The synthetic dataset's dates are fixed to August 2026. Using \`datetime.now()\` in the priority engine meant every deadline eventually went negative, and the original logic only checked \`hours\_left <= 48\` — a check negative numbers always satisfy — so genuinely overdue disputes were indistinguishable from urgent upcoming ones. Fixed by adding an explicit \`OVERDUE\` state and pinning the priority engine to a fixed simulated clock, so demo output is correct and reproducible regardless of the actual date it's run.

**\*\*Ground-truth leak in the original dataset.\*\*** The first version of the synthetic data included \`ground\_truth\_defendable\` and \`bucket\` fields directly on each dispute record — meaning the scorer could, in principle, see the answer key it was supposed to be predicting. Fixed by splitting the dataset into \`disputes.json\` (no ground truth, what the scorer actually sees) and \`evaluation\_labels.json\` (ground truth, read only by \`evaluate.py\`).

**\*\*Keeping Gemini out of the decision boundary.\*\*** The explanation layer is deliberately restricted to receiving only the scorer's already-computed output — never evaluation labels, never the ability to override a score or priority. This was a design decision enforced from the start, not a bug fix, but it's the single most important architectural property for a defense-only risk tool: the system stays auditable because the risk decision is always traceable to deterministic rules, not to a model's judgment call.

\---

**## Demo**

A Streamlit interface lets you step through individual disputes and see the full pipeline output:

\- Dispute information (ID, amount, reason code)

\- Defendability score and risk level

\- Missing critical evidence

\- Missing supporting evidence

\- Operational priority and recommended action

\- Gemini's plain-language explanation

**\*\*Example — CB-0063:\*\***

\`\`\`text

Dispute: CB-0063

Amount: ₹49,999

Reason: SUBSCRIPTION\_NOT\_CANCELLED

Defendability: 0/100

Risk: VERY LOW

Critical evidence missing:

\- Cancellation record

Supporting evidence missing:

\- Matching invoice

Priority: HIGH

Action: RETRIEVE EVIDENCE

\`\`\`

This is a merchant-facing decision-support layer — not a replacement for the underlying dispute submission system.

\---

**## Project Structure**

\`\`\`text

ai-chargeback-defendability/

│

├── data/

│   ├── generate\_disputes.py

│   ├── disputes.json

│   ├── evaluation\_labels.json

│   └── reason\_code\_evidence\_map.json

│

├── scorer/

│   └── defendability\_scorer.py

│

├── eval/

│   ├── evaluate.py

│   ├── scorer\_output.json

│   └── EVALUATION\_REPORT.md

│

├── decision/

│   └── priority\_engine.py

│

├── llm/

│   └── explain.py

│

├── demo/

│   └── run\_batch.py

│

├── app.py

├── README.md

└── .gitignore

\`\`\`

\---

**## How to Run**

**\*\*1. Install dependencies\*\***

\`\`\`bash

pip install streamlit google-genai

\`\`\`

**\*\*2. Set the Gemini API key\*\***

\`\`\`bash

export GEMINI\_API\_KEY=your\_key\_here

\`\`\`

Never commit the API key to the repository.

**\*\*3. Run the Streamlit application\*\***

\`\`\`bash

streamlit run app.py

\`\`\`

**\*\*4. Run evaluation\*\***

\`\`\`bash

python eval/evaluate.py

\`\`\`

**\*\*5. Run the batch demo\*\***

\`\`\`bash

python demo/run\_batch.py

\`\`\`

\---

**## Defense-Only Design**

This project is strictly scoped to **\*\*chargeback defense and loss prevention\*\***. It does not:

\- Generate fraudulent transactions

\- Bypass payment controls

\- Evade fraud detection

\- Facilitate unauthorized access

\- Generate offensive attack strategies

The system only evaluates evidence a merchant already has and recommends how to respond to a dispute. Gemini is constrained to explanation — the underlying risk and evidence decisions remain deterministic, inspectable, and fully auditable.
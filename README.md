# TallyLedgers

### A Financial Reconciliation Engine

> **RazorPay Buildathon: Track 04 — AI Finance Controller: Multi-source reconciliation**
> 
> Run the books and the cash position.

An agent that reconciles payment gateway transactions against bank settlement records, reports a measured match rate and accuracy, and surfaces every unresolved transaction as a categorized exception instead of silently dropping it.

---

## Table of Contents

- [The Problem](#the-problem)
- [Results](#results)
- [Approach](#approach)
- [Architecture](#architecture)
- [Configurable Thresholds](#configurable-thresholds)
- [Exception Handling](#exception-handling)
- [Application Features](#application-features)
- [Test Data](#test-data)
- [Installation](#installation)
- [Honest Limitations](#honest-limitations)
- [Tech Stack](#tech-stack)

---

## The Problem

Reconciliation between a payment gateway's transaction ledger and a bank's settlement file is still largely done by hand. Matching amounts, chasing date-shifted settlements, spotting duplicate or missing entries, and explaining discrepancies caused by fees, tax, and partial refunds are some of the activities carried out manually.

This is a **verification problem**, not a generation problem — the bar isn't "can it find some matches," it's "how many did it get right, and does it know what it doesn't know."

---

## Results

*On the included 56-record synthetic batch:*

| Metric | Value |
|--------|-------|
| Match Rate | Reported live in-app on every run |
| Precision | 100.0% |
| Recall | 100.0% |
| F1-Score | 1.0 |
| False Positive Rate | 0.0% |
| Execution Latency | ~0.2s for 52–56 records |

> **Note:** Precision and false-positive rate are the numbers that matter most for a finance tool —> a false positive means money gets reconciled against the wrong transaction, which is the costliest kind of error. Both are held at the safest possible values here: the engine never claims a match it isn't sure of.

These numbers come from a batch I generated with a known answer key. This isn't a generalisation claim - please see [Honest Limitations](#honest-limitations) .

---

## Approach

The engine runs a **tiered deterministic-first matcher**, falling back to semantic similarity only for free-text description matching — not as the primary signal for amounts or IDs, which is where naive embedding-based reconciliation tools tend to fail silently.

| Tier | Logic | Confidence |
|------|-------|------------|
| **Tier 1** | Exact UTR/reference match, amount within tolerance, same-day or date-shifted settlement (T+1/T+2/T+3) within the configured window | 0.95 – 1.00 |
| **Tier 2** | Exact UTR match, amount differs by a fee/tax deduction or partial refund pattern | 0.85 |
| **Tier 3** | Semantic similarity fallback on free-text description fields | ≥ configured cutoff |
| **Unmatched** | No counterpart found, or confidence falls below every tier's threshold — routed to the exception queue | — |

---

## Architecture
<img width="1632" height="2170" alt="Architecture" src="https://github.com/user-attachments/assets/3230b636-28f4-4f94-8d09-349c33b0503a" />

---
## Configurable Thresholds

These are exposed live in the UI, not buried in code, so the matching behavior is inspectable and defensible:

- **Amount Tolerance** — Currency-denominated allowed variance between the gateway transaction and the bank credit.
- **Settlement Window** — How many days late a settlement can post and still count as a match (banks routinely settle T+1/T+2).
- **Semantic Similarity Cutoff** — Minimum cosine similarity for the Tier 3 fallback to fire, using `all-MiniLM-L6-v2` sentence embeddings.
- **Base Currency** — All amounts normalized to one currency before comparison, with a live FX rate feed (falls back to a static offline rate table if the API is unavailable — status shown in-app).

---

## Exception Handling

Every transaction that doesn't clear a tier is routed to an exception queue with a categorized reason, **not dropped**:

- Amount mismatch beyond tolerance
- Duplicate UTR in the settlement file
- Missing counterpart (gateway transaction with no matching settlement row)
- Orphan settlement (settlement row with no matching gateway transaction)
- Partial refund adjustment

---

## Application Features

| Tab | Description |
|-----|-------------|
| **Ledger** | Full reconciliation output with every transaction tagged by match tier and confidence score. Exportable as CSV. |
| **Tier Analytics** | Distribution of matches across tiers with filtering capabilities. |
| **Exceptions** | Complete unresolved queue, filterable by category. Exportable as CSV. |
| **Accuracy** | Upload a ground-truth CSV to compute precision, recall, F1, and false-positive rate against known-correct answers. Fail/pass rows are highlighted directly in the table. |
| **Normalized Feeds** | Both source feeds after currency normalization for auditability. |
| **Engine Specifications** | Exact thresholds and mode active for the current run. |

A **Rerun Reconciliation** button re-executes the pipeline on demand and flags when configuration has changed since the last run, rather than silently recomputing on every slider tick.

---

## Test Data

The included synthetic dataset contains:
- **50 gateway transactions**
- **50 settlement rows**

Across 6 deliberately planted categories:
- Exact matches
- Date-shifted settlements (T+2)
- Amount mismatches
- Duplicate UTRs
- Missing counterparts
- Partial refunds

---

## Installation

### Prerequisites
- Python 3.10 or higher

### Local Setup

```bash
# Clone the repository
git clone https://github.com/Toph-earth/TallyLedgers.git
cd TallyLedgers

# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```


---
## Using the Application

Either:
- Upload your own CSVs, or
- Use the synthetic sample dataset

---

## Honest Limitations

> **Small Batch** — These metrics are demonstrated on a 56-record batch I generated. I haven't yet validated against an independently-labeled batch at larger scale (500+, 5,000+ records) — the matching logic is not asymptotically tested here, only correctness-tested.

> **Exact-String ID Matching** — The accuracy evaluator compares matched UTRs by exact string equality. A case or whitespace difference between the pipeline's output and a ground truth file would register as a false negative even if the match was conceptually correct — no normalization step currently guards against this.

> **Semantic Fallback is Untuned on Adversarial Input** — Short, generic transaction descriptions (e.g. "payment", "refund") can produce artificially high cosine similarity between genuinely unrelated transactions. Tier 3 is a fallback for exactly this reason — it never overrides a failed Tier 1/2 exact check — but it hasn't been stress-tested against a batch designed to break it.

> **Ground Truth Quality is Load-Bearing** — During development we found and fixed a labeling bug in our own synthetic ground truth file (a "missing counterpart" case was mislabeled as an expected match, penalizing correct behavior as a false negative). Any ground truth file — including ones you upload — is only as reliable as its labels; the evaluator can't tell the difference between the engine being wrong and the ground truth being wrong.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| **Framework** | Streamlit |
| **Data Processing** | pandas |
| **Semantic Matching** | SentenceTransformers (`all-MiniLM-L6-v2`) |

---

## Contact

- **Project Link:** [https://github.com/Toph-earth/TallyLedgers](https://github.com/Toph-earth/TallyLedgers)
- **Live app:** [https://tallyledgers.streamlit.app](https://tallyledgers.streamlit.app)

---

*Onwards!*

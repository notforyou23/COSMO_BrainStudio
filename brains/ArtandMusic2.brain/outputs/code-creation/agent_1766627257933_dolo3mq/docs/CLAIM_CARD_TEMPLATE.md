# Claim Card Template (Stage 1)

Purpose: standardized intake for claim verification with machine-validated required fields.
Validator rules (hard-fail): a claim card is invalid if **Claim Text** or **Dataset Anchor** is missing or empty.

## Intake checklist (required unless marked optional)
- [ ] Claim Text: present and concrete (single claim, no placeholders)
- [ ] Dataset Anchor: present and resolvable (exact dataset/table/field/record scope)
- [ ] Primary-source verification: at least one primary source and how it will be checked
- [ ] Owner + date captured
- [ ] Scope + assumptions (optional but recommended)

---
## 1) Claim (REQUIRED)

### Claim ID (recommended)
- claim_id:

### Claim Text (REQUIRED; hard-fail if missing/empty)
Write the claim as a single, testable statement.
- claim_text: >


---
## 2) Dataset Anchor (REQUIRED; hard-fail if missing/empty)

Provide the exact location in the data that contains the evidence for this claim.
Include enough detail for another person (or validator) to retrieve the same slice.

- dataset_anchor:
  - dataset_name:
  - dataset_version_or_date:
  - table_or_file:
  - key_fields:
  - record_filter_or_query:
  - columns_used:

Notes:
- Prefer canonical identifiers (dataset registry ID, table path, partition/date, and query).
- If using multiple datasets, list them as an array under dataset_anchor (and anchor each one).

---
## 3) Primary-Source Verification (REQUIRED)

List the primary source(s) that the claim ultimately depends on and how they will be verified.
Primary source examples: official filings, statutes, audited datasets, signed reports, raw instrument output.

- primary_sources:
  - source_title:
    source_type:  # e.g., statute, filing, registry, instrument output, signed report
    publisher_or_owner:
    url_or_citation:
    publication_date:
    retrieval_date:
    verification_method:  # how you will confirm authenticity + relevance (not just "read it")
    expected_evidence:  # what exact fact/field/line/table should match the claim

---
## 4) Measurement & Logic (recommended)

- metric_definition:
- unit_of_analysis:
- time_window:
- computation_notes:
- known_limitations:

---
## 5) Accountability (recommended)

- intake_owner:
- intake_date:  # YYYY-MM-DD
- review_owner:
- review_status:  # draft | ready_for_review | approved | rejected
- change_log:

---
## Inline example: compliant vs non-compliant (primary-source verification)

### Compliant (passes required-field checks)
claim_id: CC-0001
claim_text: >
  In Q2 2024, the reported churn rate for Product A was below 3% for paid subscribers.
dataset_anchor:
  dataset_name: analytics_subscriptions
  dataset_version_or_date: 2024-07-01
  table_or_file: mart.subscription_metrics_daily
  key_fields: [date, product, plan]
  record_filter_or_query: >
    SELECT date, product, plan, churn_rate
    FROM mart.subscription_metrics_daily
    WHERE product='A' AND plan='paid'
      AND date BETWEEN '2024-04-01' AND '2024-06-30';
  columns_used: [churn_rate]
primary_sources:
  - source_title: "Subscription Billing System Raw Export (Authoritative)"
    source_type: "system export"
    publisher_or_owner: "Finance Systems"
    url_or_citation: "internal://finance/billing/exports/subscriptions_daily?asof=2024-07-01"
    publication_date: "2024-07-01"
    retrieval_date: "2024-07-02"
    verification_method: "Verify export checksum + access logs; reconcile aggregate counts to GL revenue totals for same window."
    expected_evidence: "Daily paid-subscriber cancels and active base used to compute churn denominator/num."

### Non-compliant (fails hard)
# Missing claim_text (hard-fail) and dataset_anchor (hard-fail)
claim_id: CC-0002
primary_sources:
  - source_title: "Some blog post"
    source_type: "secondary"
    url_or_citation: "https://example.com/blog"
    verification_method: "Read it"

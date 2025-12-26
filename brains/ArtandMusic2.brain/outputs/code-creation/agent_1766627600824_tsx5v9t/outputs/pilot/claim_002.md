---
schema: claim-card
schema_version: "0.2.0"
claim_id: "claim_002"
title: "Remote work increases developer productivity by ~13%"
status: "pilot"
created_at: "2025-12-24T00:00:00Z"
created_by:
  name: "Pilot Author"
  affiliation: "COSMO Pilot"
version: "1.0.1"
content_version: "v1.0"
version_notes: "Two version fields are present and do not clearly map to a single canonical version."
provenance:
  sources:
    - citation: "Bloom, N. et al. (2015). Does Working from Home Work? Evidence from a Chinese Experiment."
      url: "https://www.aeaweb.org/articles?id=10.1257/aer.20150570"
      retrieved_at: "2025-12-20"
      source_version: "Published version (2015) vs. working paper (undated here)"
      notes: "Claim text also appears in secondary summaries; unclear which exact version was used for the 13% figure."
    - citation: "Company blog summary of the same study (date varies by mirror)."
      url: "https://example.com/remote-work-13-percent"
      retrieved_at: "2025-12-20"
      source_version: "Unknown (page shows no revision history; multiple mirrors exist)"
      notes: "Used to obtain the '13%' figure wording; may differ from the journal article metric definition."
  extraction_method: "Manual reading + secondary-summary cross-check"
  evidence_artifacts:
    - type: "pdf"
      locator: "Local PDF mentioned in notes but not attached; filename uncertain."
      sha256: null
correction_history:
  - corrected_at: "2025-02-01"
    corrected_by: "Pilot Author"
    change_summary: "Adjusted wording to 'developer productivity' from 'employee productivity'."
    reason: "Original source discusses call-center employees; mapping to developers is an interpretation step."
    supersedes_version: "1.0.0"
  - corrected_at: "2024-12-15"
    corrected_by: null
    change_summary: "Initial creation."
    reason: "Baseline entry."
    supersedes_version: "v0"
---

# Claim Card: claim_002

## Verbatim claim
"Remote work increases developer productivity by about 13%."

## Operational interpretation
- Population: software developers working remotely at least 4 days/week.
- Outcome: productivity as measured by output per unit time (not clearly defined).
- Effect size: +13% relative to in-office baseline.

## Evidence summary
- Primary study is commonly cited as showing ~13% performance increase for working from home in a randomized experiment, but it is not a software developer population.
- The 13% figure appears in multiple retellings; metric definitions vary (calls handled vs. performance ratings vs. output).

## Source/provenance ambiguity (intentional)
- Two sources are listed: a peer-reviewed article and a secondary blog summary; this card does not specify which is authoritative for the numeric effect size.
- The cited primary source has multiple versions (working paper vs. journal); this card does not pin the exact version used to compute "13%".
- Evidence artifact hashing is absent/nullable, so the exact document instance cannot be disambiguated.

## Confidence
- Level: Low to Medium
- Rationale: Numeric effect size is widely repeated, but population/metric mismatch and version uncertainty reduce reliability.

## Known limitations / risks
- Category error: call-center performance ≠ developer productivity.
- Potential publication/selection effects in which version of the study is used.
- Overgeneralization risk in policy decisions if treated as developer-specific evidence.

## Tags
remote-work, productivity, generalization-risk, version-ambiguity, provenance-ambiguity, correction-history-issues

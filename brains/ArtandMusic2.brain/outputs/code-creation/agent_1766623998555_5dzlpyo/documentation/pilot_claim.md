# Pilot claim (dataset-verification) — required intake fields demo

This document defines the single *dataset-verification pilot claim* and the **exact intake fields** that must be present to pass the updated checklist. The goal of this pilot is to prove we can **block work** unless the claim is anchored to a dataset/provenance reference (or an explicit fallback) *and* includes minimal context metadata (who/when/where).
## 1) Verbatim pilot claim text (must be copied exactly)

> “We achieve a top-5 test error rate of 15.3% on the ImageNet LSVRC-2010 contest, compared to 26.2% achieved by the second-best entry.”

Notes:
- The claim must be recorded *verbatim* (including numbers, qualifiers, and dataset/benchmark naming).
- If the source has multiple nearby metrics (e.g., LSVRC-2012 vs LSVRC-2010), the intake must preserve the exact variant referenced in the source.
## 2) Where the claim comes from (context metadata: who/when/where) — REQUIRED

These fields are mandatory to establish “who said what, when, and where”:

- **who**:
  - Primary authors/organization: Krizhevsky, Sutskever, Hinton (University of Toronto)
- **when**:
  - 2012 (paper year; NIPS 2012 workshop version widely circulated; journal version 2017)
- **where**:
  - Source type: peer-reviewed paper / technical report
  - Canonical citation:
    - Krizhevsky, A., Sutskever, I., & Hinton, G. E. (2012). *ImageNet Classification with Deep Convolutional Neural Networks.*
  - Source link: https://dl.acm.org/doi/10.1145/3065386
  - Source DOI: 10.1145/3065386

Pass condition:
- All three: who + when + where (with at least one stable identifier: DOI and/or canonical URL).

Fail condition (block work):
- Missing any of who/when/where, or “where” lacks a stable link/identifier.
## 3) Dataset/provenance anchors — REQUIRED (hard gate)

### Option A (preferred): Dataset name + DOI/link (must have both name and at least one stable locator)

- **dataset_name**: ImageNet (ILSVRC / ImageNet Large Scale Visual Recognition Challenge)
- **dataset_version_or_split**: LSVRC-2010 (as written in the claim); evaluation metric: top-5 test error
- **dataset_locator** (must include at least one):
  - Dataset landing page: https://www.image-net.org/
  - Challenge page (historical context): https://www.image-net.org/challenges/LSVRC/
  - Dataset paper DOI (acceptable anchor for the dataset definition): 10.1109/CVPR.2009.5206848
    - Deng, J. et al. (2009). *ImageNet: A Large-Scale Hierarchical Image Database.* CVPR.

Pass condition:
- dataset_name present AND at least one dataset_locator (DOI and/or stable URL) present.

Fail condition (block work):
- dataset_name missing OR no DOI/link provided for the dataset/provenance anchor.
### Option B (explicit fallback only when dataset DOI/link is genuinely unknown): research area + 2 seed papers/authors

If and only if a dataset locator cannot be provided, intake must include:
- **research_area**: (e.g., “computer vision — large-scale image classification benchmarks”)
- **seed_anchors** (minimum 2, each with author + title + link/DOI):
  1) Deng et al. (2009) ImageNet dataset paper. DOI: 10.1109/CVPR.2009.5206848
  2) Russakovsky et al. (2015) ILSVRC analysis paper. DOI: 10.1007/s11263-015-0816-y

Pass condition:
- research_area present AND at least two seed_anchors present.

Fail condition (block work):
- research_area missing OR fewer than two seed_anchors.

Important:
- For this pilot claim, Option A is expected and available; Option B is included to demonstrate the hard-requirement fallback structure.
## 4) Expected intake fields (minimum claim card payload)

A conforming claim card (human-readable example) should include at least:

- claim_text (verbatim; required)
- context:
  - who (required)
  - when (required)
  - where:
    - citation (required)
    - link_or_doi (required)
- provenance_anchors:
  - dataset:
    - name (required)
    - version_or_split (required when specified in claim)
    - doi_or_link (required unless fallback used)
  - fallback (only if dataset doi/link missing):
    - research_area (required)
    - seed_anchors (>=2; required)

This pilot passes only if:
- claim_text is verbatim (string match check is allowed for the pilot),
- dataset anchor is present (Option A), and
- who/when/where context is complete.
## 5) Validation rules (blockers) illustrated on this pilot

The validator must FAIL (block work) if any of the following is true:

1) Missing verbatim claim text:
- claim_text absent or empty.

2) Missing dataset/provenance anchors:
- dataset.name missing, OR
- dataset.doi_or_link missing AND fallback not provided, OR
- fallback provided but (research_area missing OR seed_anchors < 2).

3) Missing context metadata:
- context.who missing, OR
- context.when missing, OR
- context.where missing or lacks a stable locator (DOI/link).

Expected outcome for this pilot claim:
- PASS, because ImageNet/ILSVRC has stable dataset anchors and the source paper has a DOI/link.

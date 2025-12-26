# Intake Checklist (Claim Cards)

Purpose: prevent work on underspecified claims by hard-requiring (1) verbatim claim text, (2) dataset/provenance anchors (or explicit fallback), and (3) context metadata (who/when/where). If any **BLOCKER** fails, stop and request missing info before proceeding.

## 0) Gate: Work-Blocking Validation (must pass to start)
BLOCKER rules (fail = do not start analysis):
- **Claim text**: A verbatim quote is present (see §1).
- **Dataset/provenance anchor**: Either §2A passes, or §2B passes.
- **Context metadata**: §3 passes.

## 1) Verbatim Claim Text (BLOCKER)
Provide the claim exactly as stated (copy/paste), including hedges, qualifiers, and units.
Required:
- Verbatim claim text (1–5 sentences) in quotes.
- Source container (paper/report/post/video) + where inside it (page/section/timestamp).
- If paraphrasing is needed for internal labels, include it separately and keep verbatim text unchanged.

PASS if:
- Verbatim quote is present AND source location is specified.
FAIL if:
- Only a paraphrase/summary is provided OR quote lacks a findable location.

## 2) Dataset / Provenance Anchors (BLOCKER)
Choose **A** (preferred) or **B** (fallback). At least one must PASS.

### 2A) Dataset identified (preferred) (BLOCKER)
Required:
- Dataset name (official/common) AND
- DOI or persistent link (landing page, repository record, or canonical URL) AND
- Dataset version/date (or “unknown” with explanation) AND
- Access path (how we will obtain it: URL, repository, request).

PASS if:
- Name + DOI/link are present AND access path is feasible.
FAIL if:
- Dataset is unnamed, linkless, or not retrievable in principle.

### 2B) Fallback when dataset is unknown (BLOCKER)
Use only if no dataset can yet be named.
Required:
- Research area (specific subfield/topic) AND
- At least **two** seed anchors: papers (title+year+venue or DOI/link) and/or authors/groups (full names) that plausibly define the dataset/measurement tradition AND
- A short plan for resolving the dataset identity (1–3 sentences).

PASS if:
- Research area + ≥2 seed anchors are present AND the plan is concrete.
FAIL if:
- Research area is vague OR fewer than 2 anchors OR no plan.

## 3) Context Metadata: who / when / where (BLOCKER)
Required:
- Who: claimant (author/org) and audience (if stated).
- When: date of claim (publication date or posting date; include timezone if social).
- Where: venue/platform + geographic or institutional context if relevant (e.g., country, lab, company, school system).
- Scope qualifiers: population, setting, time period, inclusion/exclusion notes.

PASS if:
- Who+When+Where are each explicitly filled.
FAIL if:
- Any of who/when/where is missing or “unknown” without an attempt to resolve.

## 4) Minimum Evidence/Measurement Clarity (non-blocking but required before conclusions)
Provide enough to interpret the claim correctly:
- Outcome(s): what is measured, units, and evaluation window.
- Comparator/baseline: what the claim compares against (if any).
- Study type: RCT/observational/benchmarking/simulation/etc.
- Known confounders/limitations stated by authors (if available).

PASS if:
- Outcomes and comparator are clear enough to avoid category errors.
FAIL if:
- Outcomes are ambiguous or conflated (e.g., “performance” with no metric).

## 5) Intake Pass/Fail Summary (record at bottom of claim card)
Record:
- Gate status: PASS / FAIL (BLOCKED)
- Failed checks: list the exact missing items.
- Next action: the single highest-priority question to unblock.

## 6) Dataset-Verification Pilot Claim (test case)
Goal: demonstrate the gate on a “dataset verification” claim.

### 6.1 Verbatim claim text (PASS)
“MNIST is a dataset of handwritten digits consisting of 60,000 training examples and 10,000 test examples.”
Source location: MNIST project page (Yann LeCun, Corinna Cortes, Christopher J.C. Burges), description section: http://yann.lecun.com/exdb/mnist/

### 6.2 Dataset/provenance anchor (PASS via §2A)
- Dataset name: MNIST (Modified National Institute of Standards and Technology database)
- DOI/link: http://yann.lecun.com/exdb/mnist/ (canonical landing page)
- Version/date: original release (commonly cited; exact version not labeled on page)
- Access path: download links on the MNIST page (IDX files) or mirrored hosting as needed.

### 6.3 Context metadata (PASS)
- Who: Yann LeCun et al. (dataset authors/maintainers)
- When: dataset page is longstanding; claim used as the dataset’s canonical description (date not explicitly provided on the page; use retrieval date in the claim card).
- Where: dataset hosted at yann.lecun.com (web repository), originally associated with AT&T Bell Labs / research community usage.
- Scope qualifiers: handwritten digits 0–9; fixed train/test split sizes as stated.

### 6.4 Gate result (PASS)
- Claim text: PASS
- Dataset/provenance anchor: PASS
- Context metadata: PASS
Proceed to verification work only after recording retrieval date and any mirrored-source hash/checksums if used.

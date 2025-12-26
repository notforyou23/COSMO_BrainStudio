# Bibliography System Specification

This document defines (1) required BibTeX fields per entry type, (2) tagging conventions for domain/subtopic/type, (3) deduplication rules (DOI/ISBN-first), and (4) a source-quality scoring rubric.

## 1) Canonical fields & normalization (all entries)
**Required (all types):**
- `title` (use sentence case; preserve proper nouns)
- `author` (BibTeX “Last, First and Last2, First2”; include full given names when known)
- `year` (4 digits)
- `tags` (see §2; semicolon-separated)
- `quality` (integer 1–5 per rubric in §4)

**Strongly recommended (when applicable):**
- `doi` (lowercase; strip `https://doi.org/`)
- `isbn` (digits and `X` only; store 10 or 13; no hyphens/spaces)
- `url` (stable landing page; prefer publisher/arXiv)
- `urldate` (ISO `YYYY-MM-DD`)
- `abstract` (1–5 sentences; optional)
- `keywords` (comma-separated; optional)
- `note` (short provenance notes; optional)

**Normalization rules:**
- Titles: no trailing period; keep LaTeX for symbols (e.g., `{L}STM`, `$\alpha$`).
- Venues: use standard abbreviations consistently (e.g., *JMLR*, *NeurIPS*).
- `doi`: lowercase; validate pattern `10.\d{4,9}/...` when feasible.
- `isbn`: prefer ISBN-13 if known; if both exist, store ISBN-13 in `isbn` and ISBN-10 in `note`.

## 2) Tagging conventions (domain/subtopic/type)
Store tags in a single BibTeX field: `tags = {domain:<...>; subtopic:<...>; type:<...>; ...}`.

**Required tags (exactly one each):**
- `domain:<d>` where `<d>` ∈ `{ml, nlp, cv, rl, ir, dm, stats, opt, systems, security, hci, econ, theory}`
- `subtopic:<s>`: free but consistent, lowercase with hyphens (e.g., `subtopic:transformers`, `subtopic:causal-inference`)
- `type:<t>` where `<t>` ∈ `{textbook, survey, tutorial, classic, empirical, theoretical, benchmark, methods, position, standard}`

**Optional tags (0+):**
- `task:<...>` (e.g., `task:classification`, `task:ranking`)
- `data:<...>` (dataset name)
- `method:<...>` (e.g., `method:variational-inference`)
- `level:<...>` ∈ `{intro, intermediate, advanced}`
- `open:<...>` ∈ `{open-access, closed}`
- `rep:<...>` ∈ `{has-code, no-code}`

**Example:**
`tags = {domain:ml; subtopic:deep-learning; type:textbook; level:intro}`

## 3) Required fields by BibTeX entry type
Use standard BibTeX types; when in doubt choose the closest and comply with required fields below.

### `@article`
Required: `author`, `title`, `journal`, `year`, `volume` OR `number`, `pages` OR `eid`, `tags`, `quality`
Recommended: `doi`, `url`, `urldate`

### `@inproceedings`
Required: `author`, `title`, `booktitle`, `year`, `pages` OR `eid`, `tags`, `quality`
Recommended: `doi`, `url`, `urldate`, `organization`, `publisher`

### `@book`
Required: `author` OR `editor`, `title`, `publisher`, `year`, `isbn` (if exists), `tags`, `quality`
Recommended: `edition`, `address`, `url`, `urldate`

### `@incollection` (chapter in edited book)
Required: `author`, `title`, `booktitle`, `publisher`, `year`, `pages`, `editor`, `tags`, `quality`
Recommended: `doi`, `url`, `urldate`

### `@techreport`
Required: `author`, `title`, `institution`, `year`, `tags`, `quality`
Recommended: `number`, `doi`, `url`, `urldate`

### `@misc` (preprints, web standards, repos)
Required: `author` (or responsible org), `title`, `year`, `howpublished` OR `url`, `tags`, `quality`
Recommended: `doi` (if Zenodo), `eprint`/`archivePrefix` (for arXiv), `urldate`

## 4) Deduplication rules (DOI/ISBN-first)
**Goal:** one canonical entry per work; alternate versions become `note`/`url` links or separate entries only if substantively different (e.g., journal extension).

1. **DOI match (highest priority):** if two entries share the same normalized `doi`, keep one (prefer publisher version with complete metadata). Merge missing fields from the other; keep one BibTeX key.
2. **ISBN match:** for books, if `isbn` matches after normalization, treat as duplicates; prefer latest edition only when explicitly needed (otherwise keep first major edition and note later editions).
3. **Title+author+year fuzzy:** if no DOI/ISBN, consider duplicates when:
   - titles match after lowercasing and stripping punctuation/stopwords AND
   - first author last name matches AND
   - years differ by ≤ 1 (conference vs. arXiv timing).
4. **Versioning policy:** if a journal article is a substantial extension of a conference paper, keep **both** but link them:
   - add `note = {Extends/earlier version: <bibkey>}` and reciprocal note.
5. **Key naming convention:** `AuthorYYYYShortTitle` (ASCII; no spaces), e.g., `Vaswani2017Attention`.

## 5) Source-quality rubric (`quality` = 1–5)
Score the *source* (venue/credibility) and *utility* (clarity/impact), not personal preference. Use integers only.

- **5 (Gold standard):** definitive textbook/monograph from reputable publisher; or highly influential peer-reviewed work with strong evidence, clear methods, and lasting citations; or authoritative standards.
- **4 (Strong):** top-tier peer-reviewed venue (journal/conference) or widely used survey/tutorial; solid methodology and reproducibility signals (open data/code).
- **3 (Good/usable):** peer-reviewed but mid-tier venue; or well-regarded arXiv preprint with substantial community adoption; minor gaps in evaluation or clarity.
- **2 (Weak):** non-peer-reviewed reports/blogs or preliminary preprints with limited validation; ambiguous claims; hard to reproduce.
- **1 (Unreliable):** unverifiable claims, low-credibility venues, no methodology, or known issues (retractions/major errors).

**Rubric addenda (apply as adjustments, not separate fields):**
- +1 (cap at 5) if replicated by multiple independent works or adopted as a de facto standard benchmark.
- −1 (floor at 1) if results are superseded, contradicted, or the venue is predatory/opaque.

## 6) Compliance checklist (for curators)
- Entry includes required fields for its BibTeX type (§3) plus `tags` and `quality`.
- DOI/ISBN normalized and used for dedup (§4).
- Tags include exactly one `domain:*`, one `subtopic:*`, one `type:*` (§2).
- Prefer stable URLs; include `urldate` when using `url`.

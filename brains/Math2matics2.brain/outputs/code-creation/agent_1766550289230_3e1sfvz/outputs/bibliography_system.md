# Bibliography System (Canonical Spec)

This document defines the reproducible workflow used to curate a seed bibliography dataset and deterministically generate canonical outputs, especially `outputs/references.bib`.

## 1) Canonical objects and required fields

Each reference is a single record with the following required fields (all strings unless noted):

- `id`: Stable internal identifier (dataset key). ASCII, lowercase, `[a-z0-9_./-]`, must be unique.
- `type`: One of: `article`, `inproceedings`, `book`, `incollection`, `phdthesis`, `techreport`, `misc`.
- `title`
- `year`: 4-digit year.
- `authors`: List of author strings in display order, each as `"Family, Given"` (e.g., `"Turing, Alan M."`).
- `tags`: Object with:
  - `kind`: exactly one of `{seminal, survey, textbook}`.
  - `topics`: non-empty list of topic tags (see §2).
- `venue`: Journal / conference / publisher / institution (depending on type).
- `url` **or** `doi`: At least one must be present. If both exist, keep both.
- `notes` (optional): Freeform; not used for ordering/dedup.

Type-specific required fields:
- `article`: `journal` (alias of `venue` is allowed but canonical output uses `journal`), optional `volume`, `number`, `pages`.
- `inproceedings`: `booktitle` (alias of `venue`), optional `pages`, `organization`.
- `book`: `publisher` (alias of `venue`), optional `edition`, `isbn`.
- `techreport`: `institution` (alias of `venue`), optional `number`.
- `phdthesis`: `school` (alias of `venue`).
- `misc`: must still satisfy core required fields; use `howpublished` in BibTeX.

Normalization rules:
- Trim whitespace; collapse internal whitespace runs to single spaces in `title`, `venue`.
- Use ASCII hyphen-minus in pages (e.g., `123-145`).
- Preserve author punctuation; do not reorder authors.

## 2) Tagging schema

### 2.1 Kind tag (required)
Exactly one of:
- `seminal`: foundational primary sources.
- `survey`: overview / review / taxonomy / tutorial paper.
- `textbook`: book-length pedagogical reference.

### 2.2 Topic tags (required)
- `topics` is a list of lowercase slugs: `[a-z0-9_]+`.
- Recommended topics (extensible): `ai`, `ml`, `dl`, `rl`, `nlp`, `cv`, `probability`, `optimization`, `information_theory`, `causality`, `bayesian`, `stats`, `control`, `algorithms`, `distributed_systems`, `security`, `networks`, `systems`, `foundations`, `ethics`.
- A record must have **≥1** topic.
- Topics are for filtering/grouping only; they do not affect BibTeX entry type.

## 3) Deterministic BibTeX generation

### 3.1 BibTeX key format
Canonical key (`bibkey`) is derived deterministically:
`{first_author_family}{year}{slug(title)}`
- `first_author_family`: lowercase alphanumeric from first author family name (strip punctuation/spaces).
- `slug(title)`: first 6–10 significant words from title, lowercase, alphanumeric only, stopwords removed (`a, an, the, of, and, to, in, for, on, with`), concatenated.
- If collision occurs, append `a`, `b`, `c`… by stable lexicographic order of full normalized citation string (see §3.3).

### 3.2 Field mapping to BibTeX
- `authors` -> `author` joined by `" and "`.
- `venue` maps by `type`:
  - `article`: `journal`
  - `inproceedings`: `booktitle`
  - `book`: `publisher`
  - `techreport`: `institution`
  - `phdthesis`: `school`
- Always include: `title`, `author`, `year`, and the mapped venue field.
- Include `doi` and/or `url` when present.
- Emit tags as deterministic `keywords` field:
  `keywords = {kind:K; topics:t1,t2,...}`
  where `K` is one of `seminal|survey|textbook` and topics are sorted.

### 3.3 Ordering and formatting
- Canonical order in `references.bib`:
  1) Sort by `year` ascending,
  2) then by `first_author_family` ascending,
  3) then by `title` ascending,
  4) then by `id` ascending.
- Canonical formatting:
  - Two-space indentation for fields.
  - One field per line: `  field = {value},`
  - Final field line has no trailing comma.
  - UTF-8 output; do not TeX-escape unless required by BibTeX (prefer literal Unicode).

## 4) Deduplication policy

Deduplication is deterministic and conservative; it prevents accidental loss of distinct editions.

### 4.1 Primary identity signals (in priority order)
1) Same DOI (case-insensitive) => duplicates.
2) Same ISBN (if present) => duplicates (books).
3) Otherwise, compute a *fingerprint*:
   - `norm_title`: lowercase, remove punctuation, collapse spaces.
   - `first_author_family`: normalized as in §3.1.
   - `year`
   Fingerprint = `first_author_family + "|" + year + "|" + norm_title`

If two records share a fingerprint, treat as duplicates **unless**:
- They are different `type` (e.g., preprint vs journal) AND both have distinct DOIs/URLs; then keep both but add a note explaining relationship.

### 4.2 Merge rule (when deduping)
When duplicates are confirmed, keep a single canonical record chosen by:
1) record with DOI,
2) else record with URL,
3) else lexicographically smallest `id`.
Merge fields by taking the union where possible:
- `tags.topics`: union, then sort.
- `tags.kind`: if conflict, prefer `survey` > `textbook` > `seminal` only when clearly supported; otherwise keep the canonical record’s kind and log conflict (build script responsibility).
- Prefer longer `venue` string if one is abbreviation and the other expanded.

## 5) Validation checklist (build step)
A record is valid iff:
- All required fields exist and are non-empty.
- `year` is 4 digits.
- `authors` list is non-empty and each contains a comma.
- `tags.kind` is exactly one allowed value.
- `tags.topics` is non-empty, unique, and lowercase slugs.
- At least one of `doi` or `url` exists.

This spec is the single source of truth for enforcement and deterministic generation.

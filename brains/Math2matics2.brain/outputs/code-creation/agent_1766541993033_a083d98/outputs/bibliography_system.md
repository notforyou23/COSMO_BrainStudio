# Bibliography System (Workflow + BibTeX Requirements + Tags + Intake Checklist)

This document standardizes how we collect, tag, and maintain references across target domains (LLMs/ML, software engineering, bibliometrics/IR, research methods, and ethics/policy).

## 1) Workflow (source → curated BibTeX)

1. **Discover**: identify candidate sources (papers, standards, datasets, tools, blog posts only if authoritative).
2. **Verify**: confirm canonical metadata (title, authors, venue, year, DOI/URL); prefer publisher/DOI landing pages.
3. **Ingest**:
   - Create/append a BibTeX entry in `outputs/references.bib`.
   - Attach tags via `keywords = {…}` (see taxonomy below).
   - Add persistent identifiers: `doi`, `url`, and (if available) `eprint`/`arxivId`.
4. **Normalize**:
   - Use consistent citekeys (see §2.4).
   - Use `title = {...}` with proper capitalization protected by braces for acronyms/proper nouns (e.g., `{LLM}`, `{BERT}`).
   - Prefer `doi` over long URLs; keep `url` as the access route.
5. **Quality check**:
   - Required fields present (see §2).
   - `year` matches publication; `month` optional.
   - `keywords` contains at least: one `domain:*` + one `method:*` or `topic:*`.
6. **Use**: cite via citekey; never cite raw URLs in manuscripts when a citable artifact exists.
7. **Maintain**:
   - Deduplicate by DOI/arXiv.
   - Update `note` only for curation remarks (e.g., “survey”, “replication package available”).
   - Record access date only for web resources (`urldate`).
## 2) BibTeX Requirements

### 2.1 Core required fields (all entries)
- `title`
- `author` (or `editor` when appropriate)
- `year`
- `keywords` (tag list; see §3)
- One stable locator: `doi` **or** `url` (prefer both when available)

Recommended whenever available: `abstract`, `publisher`, `month`, `note`, `language`.

### 2.2 Entry-type specific required fields
| Type | Required fields (in addition to core) |
|---|---|
| `@article` | `journal`, `volume` (if known), `number` (if known), `pages` (or `eid`) |
| `@inproceedings` | `booktitle`, `pages` (or `eid`), `organization`/`publisher` (if known) |
| `@proceedings` | `title`, `year`, `editor` (if applicable), `publisher`/`organization` |
| `@book` | `publisher`, `address` (optional), `edition` (if relevant) |
| `@incollection` | `booktitle`, `publisher`, `editor` (if applicable), `pages` |
| `@techreport` | `institution`, `number` (if available) |
| `@phdthesis` / `@mastersthesis` | `school` |
| `@misc` / `@online` | `url`, `urldate` (ISO date), `howpublished` (optional) |
| `@dataset` (BibLaTeX-style) | `publisher`/`institution`, `version` (if any), `url`/`doi` |

### 2.3 Identifier fields (use when applicable)
- DOI: `doi = {10.xxxx/…}`
- arXiv: `eprint = {YYYY.NNNNN}`, `archivePrefix = {arXiv}`, `primaryClass = {cs.CL}`
- PubMed: `pmid`, `pmcid` (optional)
- Software: `version`, `commit`, `repository` (in `url` or `howpublished`), `license` (in `note` if needed)

### 2.4 Citekey convention
Format: `FirstAuthorYYYY_ShortTitle` (ASCII, no spaces).
- Example: `Vaswani2017_Attention`
- Use `EtAl` only if needed to avoid collisions: `Smith2020EtAl_Method`.
- If multiple same-year same-author: append `a`, `b`, … (e.g., `Smith2020a_…`).
## 3) Tagging Taxonomy (use in `keywords = {...}`)

### 3.1 Syntax rules
- Comma-separated list; lowercase; no spaces around colons.
- Use 3–8 tags per entry.
- Must include: **one** `domain:*` + **one** `topic:*` or `method:*`.

### 3.2 Domain tags (pick ≥1)
- `domain:llm` (LLMs, prompting, alignment)
- `domain:ml` (general ML, representation learning)
- `domain:nlp`
- `domain:software-engineering`
- `domain:information-retrieval`
- `domain:bibliometrics` (citation analysis, science of science)
- `domain:research-methods` (study design, validity, reproducibility)
- `domain:ethics-policy` (governance, fairness, privacy)

### 3.3 Topic tags (pick as needed)
- `topic:transformers`, `topic:retrieval-augmented-generation`, `topic:evaluation`
- `topic:replication`, `topic:reproducibility`, `topic:benchmarking`
- `topic:code-search`, `topic:static-analysis`, `topic:testing`
- `topic:systematic-review`, `topic:metadata`, `topic:citation-networks`
- `topic:privacy`, `topic:bias`, `topic:security`

### 3.4 Method/Artifact tags
- Methods: `method:survey`, `method:systematic-review`, `method:experiment`, `method:case-study`, `method:theory`
- Artifacts: `artifact:dataset`, `artifact:software`, `artifact:standard`, `artifact:benchmark`

### 3.5 Status/Quality tags (optional but useful)
- `status:seminal`, `status:review`, `status:replication`, `status:negative-results`
- `quality:peer-reviewed`, `quality:preprint`, `quality:standard`, `quality:blog-authoritative`
## 4) Intake Checklist (for every new reference)

### Metadata
- [ ] Correct entry type chosen (`@article`, `@inproceedings`, `@techreport`, …)
- [ ] Title matches canonical source; acronyms/proper nouns braced
- [ ] Author list complete and ordered; no “and others” unless source uses it explicitly
- [ ] Venue fields correct (`journal` or `booktitle`), plus volume/issue/pages/eid when available
- [ ] Year correct; month optional

### Identifiers & access
- [ ] DOI added when available
- [ ] URL added (landing page preferred); `urldate` added for web-only items
- [ ] arXiv fields added for preprints (`eprint`, `archivePrefix`, `primaryClass`)

### Tagging & curation
- [ ] `keywords` includes ≥1 `domain:*` and ≥1 `topic:*` or `method:*`
- [ ] Add `artifact:*` when the source introduces a dataset/tool/standard
- [ ] Add `status:*` only when justified (e.g., widely cited or explicitly a survey)
- [ ] Optional: short curation `note` (one sentence max; no subjective language)

### Hygiene
- [ ] Citekey conforms to §2.4 and is unique
- [ ] No duplicate entries (check DOI/arXiv/title)
- [ ] BibTeX compiles (balanced braces; no stray commas)

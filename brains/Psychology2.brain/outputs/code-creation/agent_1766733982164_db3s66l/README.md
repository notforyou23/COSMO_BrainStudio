# claims_audit — Atomic-claim auditing with retrieval + tiered metrics

This project audits model outputs at the *atomic claim* level. Each claim is labeled as:
- **supported**: evidence in the curated reference corpus supports the claim as stated
- **unsupported**: evidence contradicts the claim as stated
- **insufficient**: corpus lacks enough evidence to support or contradict (including ambiguity)

The pipeline:
1) decompose text → atomic claims (structured)
2) retrieve candidate evidence spans from a small curated corpus
3) adjudicate each claim (supported/unsupported/insufficient)
4) compute tiered false-accept + abstain metrics
## 1) Atomic-claim schema

An **atomic claim** is the smallest self-contained proposition that can be checked against evidence.

Recommended machine-readable fields (Pydantic-friendly):

- `id` (str): stable claim identifier (e.g., `"c_0007"`)
- `source_id` (str): where the claim came from (doc/chat/paragraph id)
- `text` (str): original claim text (human-readable)
- `subject` (str): entity or group being described
- `predicate` (str): relation/verb phrase (normalized if possible)
- `object` (str | None): value/entity acted on or equated to
- `qualifiers` (dict): optional keyed modifiers such as:
  - `quantity` (str|float|None) e.g., `"15%"`, `0.15`
  - `unit` (str|None) e.g., `"kg"`, `"USD"`
  - `location` (str|None) e.g., `"California"`
  - `population` (str|None) e.g., `"adults"`
  - `condition` (str|None) e.g., `"under inflation-adjusted terms"`
- `timeframe` (dict|None): `{ "start": "YYYY-MM-DD"|None, "end": "YYYY-MM-DD"|None, "as_of": "YYYY-MM-DD"|None }`
- `modality` (str): one of `["assertion","prediction","hypothesis","recommendation","possibility"]`
- `polarity` (str): `["positive","negative"]` (e.g., “X did” vs “X did not”)
- `normalization` (dict): canonical forms used for matching, e.g.:
  - `entities` (list[str]): normalized entity ids/names
  - `value` (str|float|None): normalized numeric value
  - `predicate_canonical` (str|None)
- `notes` (str|None): optional annotation/assumptions

Design rules:
- One claim = one checkable proposition (avoid “and”, “or”, multi-part chains).
- Keep qualifiers explicit (time, location, population, units).
- Prefer canonical, unambiguous entities and quantities in `normalization`.
## 2) Labeling rules

Label each atomic claim using *only the curated reference corpus*:

### supported
Assign **supported** if the evidence spans *directly entail* the claim under the same qualifiers.
- Numeric claims must match within an explicitly defined tolerance (if used) or exact stated bounds.
- If evidence supports a weaker statement than the claim (claim is stronger/more specific), do **not** mark supported.

### unsupported
Assign **unsupported** if the corpus includes evidence that *contradicts* the claim.
- Contradiction can be direct (“X is false”) or via mutually exclusive facts (e.g., different date/value when the claim asserts a specific one).
- If multiple sources disagree in-corpus, treat as **insufficient** unless the corpus has an explicit resolution rule (e.g., a designated “gold” doc).

### insufficient
Assign **insufficient** when:
- No relevant evidence is found in the corpus
- Evidence is relevant but incomplete/ambiguous
- Claim depends on unstated assumptions not grounded in the corpus
- The claim is underspecified (missing timeframe/location/population) and cannot be safely resolved

Common edge cases:
- Paraphrases: allowed if meaning is preserved.
- Hedged language: “may/could” tends toward **insufficient** unless evidence establishes the possibility/likelihood explicitly.
- Definitions/terminology: if the corpus defines terms, use those definitions for adjudication.
## 3) Curated reference corpus format

The reference corpus is intentionally small and curated. It is meant to be:
- auditable (human-readable evidence spans)
- searchable (concatenated text fields)
- versionable (stable doc ids and span offsets)

### Document record (JSONL or YAML list)

Each document:
- `doc_id` (str): stable unique id (e.g., `"doc_001"`)
- `title` (str)
- `text` (str): full plain text (preferred for offset-based spans)
- `source` (str|None): URL/citation string
- `created_at` (str|None): ISO date
- `meta` (dict|None): arbitrary metadata

Example JSONL (one per line):
{"doc_id":"doc_001","title":"Example Report","text":"...full text...","source":"https://...","created_at":"2024-05-01","meta":{"domain":"policy"}}

### Evidence span record

Evidence spans link specific passages to claims or topics:
- `span_id` (str): stable id (e.g., `"span_0003"`)
- `doc_id` (str): points to a document
- `start` / `end` (int): character offsets into `text` (half-open interval)
- `quote` (str): optional redundant snippet for readability (should match offsets)
- `tags` (list[str]|None): e.g., `["definition","statistic"]`
- `meta` (dict|None): optional, e.g. page numbers

Example:
{"span_id":"span_0003","doc_id":"doc_001","start":120,"end":240,"quote":"...","tags":["statistic"]}

Validation expectations:
- Offsets must be within the document text bounds.
- `quote` (if provided) should equal `text[start:end]` after normalization rules defined by the project (if any).
## 4) Retrieval + audit pipeline usage

Typical flow (conceptual):

1) Build a search index from corpus docs (and/or evidence spans).
2) For each atomic claim, retrieve top-k candidate passages.
3) Produce an audit record containing:
   - claim fields
   - retrieved passages (doc_id, span offsets/snippets, scores)
   - adjudicated label (supported/unsupported/insufficient)
   - rationale (brief; references doc_id/span ids)

Suggested retrieval interface:
- input: claim (use `text` + normalized fields)
- output: ranked list of `RetrievedItem`:
  - `doc_id`, `span_id` (optional), `snippet`, `score`, and provenance metadata

Suggested audit output (JSONL):
{"claim_id":"c_0007","label":"supported","retrieval":[{"doc_id":"doc_001","span_id":"span_0003","score":0.42}],"rationale":"doc_001 span_0003 states ...","reviewer":"auto|human","timestamp":"..."}
## 5) Tiered false-accept + abstain metrics

Let true labels be in {S, U, I} for supported/unsupported/insufficient.
Let the system output be either:
- a predicted label in {S, U, I}, or
- **abstain** (no decision) if retrieval is empty/low-confidence, or policy requires.

### Core counts (per claim)
- `n`: total claims
- `abstain`: number of abstentions
- `answered`: n - abstain
- Confusion matrix over answered claims: counts of true vs predicted among {S,U,I}

### False-accept (FA)
Define “false-accept” relative to an *accept set* A (labels we treat as “acceptable to assert”).
Common choices:
- **Tier 1 (strict)**: A = {S}
  - FA₁: predicted S when true ∈ {U, I}
- **Tier 2 (lenient)**: A = {S, I}
  - FA₂: predicted ∈ {S, I} when true = U (i.e., accepting something contradicted)

Report FA as rates:
- `FA_tier / answered` (conditional on making a decision)
- optionally also `FA_tier / n` (unconditional; incorporates abstentions)

### Abstain metrics
- `AbstainRate = abstain / n`
- **Coverage**: `answered / n`
- Optional: **Selective risk** at each tier:
  - `SelectiveFA_tier = FA_tier / answered` (same as FA rate conditional on answering)

### Recommended reporting bundle
- Coverage (answered/n)
- Tier-1 FA rate (strict) conditional + unconditional
- Tier-2 FA rate (lenient) conditional + unconditional
- Full 3-way confusion matrix on answered claims
- Breakdown by claim type (numeric, temporal, definitional) using `qualifiers/tags` if available

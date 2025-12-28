# DOI test set + provenance (curated, small, edge-case focused)

This document defines (1) a small curated DOI test set meant to exercise end-to-end DOI resolution and metadata normalization, (2) a deterministic failure-reason taxonomy, and (3) the exact output schemas for JSON/CSV/logs including explicit provenance fields.

Scope: The pipeline is expected to accept a DOI string, resolve it to a landing URL (following redirects), attempt metadata acquisition (via registry APIs and/or landing-page parsing), normalize core fields, and emit stable machine-readable outputs with structured provenance.
## Curated DOI test set (v1)

Design goals:
- Cover redirect behaviors (http→https, dx.doi.org→doi.org, publisher hops)
- Cover access friction (paywalls, consent/interstitials) without treating them as fatal when metadata can be obtained elsewhere
- Cover “multiple editions / versions” patterns (same title across different DOIs, errata, retractions)
- Include non-ASCII / punctuation in titles/authors when available
- Include at least one DOI that is expected to fail (synthetic/invalid) to validate failure coding

Notes:
- The test set is intentionally small to keep runs fast and logs readable.
- Each record is identified by `test_id`; DOIs may change ownership/landing URLs over time, so provenance fields are mandatory for reproducibility.

### Test cases

| test_id | doi | expected_primary_path | edge_case_coverage | expected_outcome |
|---|---|---|---|---|
| T01 | 10.1038/nphys1170 | doi resolver → publisher | canonical high-traffic DOI, redirect chain | success |
| T02 | 10.1126/science.169.3946.635 | doi resolver → publisher | classic DOI, older article, possible paywall | success |
| T03 | 10.1145/3368089.3409741 | doi resolver → ACM | paywall likely; validate non-fatal paywall handling | success |
| T04 | 10.1371/journal.pone.0000308 | doi resolver → PLOS | open access; validate rich metadata | success |
| T05 | 10.1109/5.771073 | doi resolver → IEEE | legacy DOI format; possible paywall | success |
| T06 | 10.1016/S0140-6736(20)30183-5 | doi resolver → Elsevier | S-number/issue-style DOI; paywall likely | success |
| T07 | 10.1007/s00134-020-05991-x | doi resolver → Springer | consent/interstitial common; redirects | success |
| T08 | 10.5281/zenodo.3727209 | doi resolver → Zenodo | dataset/software style; non-article metadata | success |
| T09 | 10.1093/nar/gkaa1105 | doi resolver → Oxford | redirects; mixed HTML/meta tags | success |
| T10 | 10.0000/this-does-not-exist | resolver fails | invalid/synthetic DOI to force failure taxonomy | failure (NOT_FOUND/INVALID_DOI) |

Implementation guidance:
- The server should store this test set as a static JSON/YAML/CSV or embed it for CLI test runs; this doc is the source-of-truth rationale and expected coverage, not the runtime fixture itself.
## Provenance requirements (per DOI record)

Every output record (success or failure) MUST include:

- `input_doi` (string): the DOI provided by the client (exactly as received)
- `normalized_doi` (string|null): lowercase, trimmed, DOI prefix stripped, validated (e.g., `10.xxxx/yyy`); null on unrecoverable parse
- `landing_url` (string|null): final URL after redirect resolution (or best-known URL if resolution partially succeeds)
- `accessed_at` (string): ISO-8601 UTC timestamp when network access for this DOI began (e.g., `2025-12-26T05:09:45Z`)
- `parsing_method` (string): one of the method identifiers defined below
- `failure_reason_code` (string|null): deterministic code from taxonomy below; null on success
- `provenance_chain` (array): ordered steps taken, each with `step`, `at`, `url`, `status`, and `note` (minimal but sufficient for debugging)

`accessed_at` is required even for immediate validation failures (set at request start).
## Parsing methods (enumeration)

`parsing_method` is a single best descriptor for the metadata source ultimately used:

- `crossref_api`: metadata from Crossref REST
- `datacite_api`: metadata from DataCite REST
- `doi_org_content_negotiation`: metadata via doi.org content negotiation (e.g., CSL-JSON/BibTeX)
- `landing_page_meta_tags`: HTML meta tags (citation_*, og:, etc.)
- `landing_page_schema_org`: JSON-LD schema.org parsing
- `hybrid`: merged metadata from multiple sources (must document merge in `provenance_chain`)
- `none`: no metadata extracted (failures)

If multiple sources are queried, record the final method used in `parsing_method` and list all attempts in `provenance_chain`.
## Failure reason code taxonomy (deterministic)

Exactly one `failure_reason_code` must be set for failures; use the most specific applicable code.

Validation / input:
- `INVALID_DOI_FORMAT`: cannot normalize/validate DOI syntax
- `EMPTY_INPUT`: blank or missing DOI

Resolution / HTTP:
- `DOI_RESOLUTION_FAILED`: doi resolver unreachable or unexpected error
- `NOT_FOUND`: resolver returns 404/410 or registry indicates DOI does not exist
- `TOO_MANY_REDIRECTS`: redirect loop or exceeds max hops
- `DNS_ERROR`: name resolution failure
- `TIMEOUT`: network timeout (connect/read)
- `HTTP_4XX`: other client error (record status in logs)
- `HTTP_5XX`: upstream server error (record status in logs)

Access friction (non-fatal when metadata obtained elsewhere; fatal only if no alternative works):
- `PAYWALL_BLOCKED`: page requires subscription/login and no metadata source succeeded
- `CONSENT_INTERSTITIAL`: blocked by cookie/consent wall and no metadata source succeeded
- `ROBOT_BLOCKED`: 403/429 or bot protection and no metadata source succeeded
- `CONTENT_TYPE_UNSUPPORTED`: non-HTML/non-parseable content where required

Parsing / metadata:
- `METADATA_NOT_FOUND`: requests succeeded but no usable metadata extracted
- `METADATA_PARSE_ERROR`: malformed JSON/HTML prevented extraction
- `NORMALIZATION_ERROR`: extracted metadata could not be normalized to schema

Internal:
- `INTERNAL_ERROR`: unexpected exception; must be logged with stack trace

Rule: paywall/consent/robot codes should be used only when they are the terminal reason preventing metadata extraction.
## Normalized output schemas

### JSON record schema (one record per DOI)

Records are emitted as JSON objects with stable keys. Required keys are marked (R).

Top-level:
- (R) `run_id` (string): unique per server run/batch
- (R) `test_id` (string|null): populated when processing the curated test set; null otherwise
- (R) `input_doi` (string)
- `normalized_doi` (string|null)
- `status` (string): `ok` or `error`
- `title` (string|null)
- `author` (array|null): list of `{family, given, orcid}` (strings or null)
- `container_title` (string|null)
- `issued` (string|null): ISO date (YYYY, YYYY-MM, or YYYY-MM-DD)
- `publisher` (string|null)
- `type` (string|null): normalized work type (e.g., article-journal, dataset)
- `url` (string|null): best canonical URL from metadata (may differ from landing_url)
- (R) `provenance` (object):
  - (R) `landing_url` (string|null)
  - (R) `accessed_at` (string)
  - (R) `parsing_method` (string)
  - (R) `failure_reason_code` (string|null)
  - (R) `provenance_chain` (array of objects):
    - (R) `step` (string) e.g., `normalize_input`, `resolve_doi`, `fetch_crossref`, `fetch_landing`, `parse_jsonld`, `export`
    - (R) `at` (string): ISO-8601 UTC timestamp
    - `url` (string|null)
    - `status` (string|null): e.g., `ok`, `error`, HTTP status text/code
    - `note` (string|null): short human-readable note (no secrets)

### JSONL
If exported as JSONL, each line is a standalone JSON record matching the schema above.
### CSV schema (one row per DOI)

CSV is a flattened view of the JSON record. Columns MUST appear in this exact order:

1. `run_id`
2. `test_id`
3. `input_doi`
4. `normalized_doi`
5. `status`
6. `title`
7. `container_title`
8. `issued`
9. `publisher`
10. `type`
11. `url`
12. `author_count`
13. `authors` (semicolon-separated `Family, Given` pairs)
14. `orcid_list` (semicolon-separated ORCIDs)
15. `provenance.landing_url`
16. `provenance.accessed_at`
17. `provenance.parsing_method`
18. `provenance.failure_reason_code`

Null values are empty strings. Lists are joined deterministically (original order when available, otherwise sorted by family/given).
### Log schema (structured, per run)

Logs are newline-delimited JSON objects (NDJSON). Each log line MUST include:

- `ts` (string): ISO-8601 UTC timestamp
- `level` (string): DEBUG/INFO/WARNING/ERROR
- `run_id` (string)
- `event` (string): stable event name (e.g., `doi.start`, `doi.resolve`, `doi.fetch.crossref`, `doi.parse`, `doi.done`, `export.done`)
- `input_doi` (string|null)
- `normalized_doi` (string|null)
- `test_id` (string|null)
- `url` (string|null)
- `http_status` (int|null)
- `failure_reason_code` (string|null)
- `message` (string): short message
- `extra` (object|null): small structured payload (durations, hop count, content-type); must not include secrets

Minimum logging expectations:
- One `doi.start` and one terminal `doi.done` per DOI
- On failure: log the chosen `failure_reason_code` and the decisive step
- On success: log `parsing_method` and key provenance URLs
## Reproducibility checklist

A run is considered reproducible if the outputs include:
- immutable `run_id`
- per-record `accessed_at` timestamps
- resolved `landing_url` (final after redirects when possible)
- deterministic `failure_reason_code` on errors
- `provenance_chain` sufficient to re-run the same strategy and debug drift

This doc defines the contract that `api_server.py` and related modules must satisfy when running the curated DOI test set end-to-end.

# Fixed DOI test set and provenance

This document defines the **small, fixed DOI test set** used by `api_server.py` to run the end-to-end DOI resolution pipeline and to generate:
- `runtime/_build/tables/doi_results.csv`
- `runtime/_build/reports/doi_run_report.json`

The goals of the test set are to (1) exercise Crossref- and DataCite-style DOIs, (2) include a few controlled failures to validate error reporting, and (3) remain stable and small enough to run quickly in CI/local development.
## DOI test set (fixed)

The pipeline uses the following DOIs **exactly as listed** (case/whitespace may vary in inputs, but the pipeline should normalize before resolution):

1. `10.1038/nphys1170`  (Crossref; canonical Nature article DOI)
2. `10.1145/3368089.3409741` (Crossref; ACM proceedings-style DOI)
3. `10.1109/5.771073` (Crossref; IEEE journal/article DOI)
4. `10.1371/journal.pone.0262698` (Crossref; PLOS journal article DOI)
5. `10.48550/arXiv.1706.03762` (DataCite; arXiv DOI via DataCite)
6. `10.5061/dryad.5d7m0` (DataCite; Dryad dataset DOI)
7. `10.5281/zenodo.3242074` (DataCite; Zenodo record DOI)

Intentional negative tests (to validate explicit failure reasons):
8. `10.9999/this-doi-does-not-exist` (syntactically plausible; expected not found)
9. `not_a_doi` (invalid format; expected validation failure)
## Provenance and selection criteria

Selection criteria for the fixed set:
- **Provider coverage:** include DOIs commonly resolved via Crossref (publishers) and DataCite (repositories/datasets).
- **Stability:** prefer widely cited, long-lived records (Nature/ACM/IEEE/PLOS) and major repositories (arXiv/Dryad/Zenodo).
- **Metadata richness:** include items likely to return titles/authors/issued dates for checking end-to-end extraction.
- **Failure-mode coverage:** include:
  - an **invalid DOI string** to ensure the validator reports a clear, non-HTTP failure; and
  - a **well-formed but nonexistent DOI** to ensure the resolvers report a clear not-found failure.

Notes:
- The set is intentionally small to keep runtime bounded and to reduce flakiness from rate limits.
- The set is “fixed” to make runs comparable over time; metadata may still drift if providers update records.
## What counts as “success” vs “failure”

A DOI run is evaluated **per DOI**. Each DOI result is classified as:

### Success
A DOI is a success when:
- it passes validation/normalization, and
- at least one provider returns a resolvable record with usable metadata, and
- the pipeline returns a structured result with `status = "success"`.

Successful results should include:
- the normalized DOI,
- the provider that succeeded (e.g., `crossref` or `datacite`),
- key metadata fields when available (e.g., title, creators/authors, container/journal, published/issued date),
- the resolved landing URL if provided by the source.

### Failure
A DOI is a failure when **no provider returns usable metadata**, or when the DOI cannot be processed. Failures must be explicit, stable, and human-interpretable: a **failure category** plus a **reason**.

Failures are expected for the two negative tests:
- `not_a_doi` → validation failure
- `10.9999/this-doi-does-not-exist` → not found (across providers)
## Failure categories and reason interpretation

The pipeline/report should use a small set of consistent categories. The exact field names may vary, but the report and CSV should preserve both a **category** and a **reason** (free text) per DOI.

Recommended categories (examples of reasons):
- `invalid_doi`: failed normalization/validation (e.g., "does not match DOI pattern").
- `not_found`: provider returned 404 / "resource not found" / empty record.
- `provider_error`: unexpected 5xx/invalid payload from a provider.
- `rate_limited`: 429 or explicit rate-limit response; should indicate whether retries were attempted.
- `timeout`: request exceeded timeout.
- `network_error`: DNS/connection/TLS errors.
- `parse_error`: response received but could not be parsed/mapped to expected schema.
- `no_metadata`: response succeeded but did not contain minimum required fields.
- `all_providers_failed`: used when multiple providers were attempted; the reason should summarize the per-provider outcomes.

Interpretation guidance:
- Prefer **deterministic** reasons (HTTP status, exception class, provider message) over vague text.
- When multiple providers are tried, preserve a per-provider trace in the JSON report and summarize in CSV.
## Output artifacts (what to look for)

### `runtime/_build/tables/doi_results.csv`
A row-per-DOI table intended for quick inspection. Each row should include at least:
- `input_doi`: the DOI as read from the fixed test set
- `normalized_doi`
- `status`: `success` or `failure`
- `provider`: provider that succeeded, or last/primary provider attempted
- `failure_category` and `failure_reason` (empty for success)
- key metadata fields when present (title, year/date, authors/creators, url)
- timing fields if available (e.g., total_ms)

### `runtime/_build/reports/doi_run_report.json`
A structured run report intended for debugging and reproducibility. It should include:
- run metadata (timestamp, pipeline version/schema version)
- aggregate counts (total, successes, failures, by-category)
- per-DOI detailed records, including:
  - validation outcome
  - providers attempted in order
  - per-provider status/error mapping
  - final selected metadata (if success)
  - final failure category/reason (if failure)

This documentation is the reference for interpreting the success/failure fields in those artifacts.

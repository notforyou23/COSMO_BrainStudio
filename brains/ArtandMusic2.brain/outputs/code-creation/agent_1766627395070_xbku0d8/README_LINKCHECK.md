# Link-check runner (QA)

This project includes a small link-check runner that:
- reads exemplar URLs from case-study JSON files,
- performs HTTP(S) checks (status + redirect chain),
- writes a machine-readable report JSON and a human-readable Markdown summary.

Outputs are written under: `runtime/outputs/qa/`.
## How to run

From the project root (example):
- `python scripts/linkcheck_runner.py`

Common CLI patterns (exact flags may vary by implementation):
- `python scripts/linkcheck_runner.py --cases ./case_studies --out runtime/outputs/qa`
- `python scripts/linkcheck_runner.py --case-glob "**/*.case_study.json"`

Expected outputs:
- `runtime/outputs/qa/linkcheck_report.json`
- `runtime/outputs/qa/LINKCHECK_SUMMARY.md`
## Inputs: how URLs are discovered

The runner searches case-study JSON files and extracts “exemplar URLs” (links to sources, references, or external pages) from known URL-like fields.

Typical extraction behavior:
- scans known keys such as: `url`, `source_url`, `reference_url`, `links`, `references`, `citations`
- also scans nested objects/lists when present
- only keeps `http://` and `https://` links
- de-duplicates URLs across all case studies

If a URL is present multiple times, it should appear once in the report with aggregated provenance (e.g., which case-study file(s) referenced it).
## What is checked

For each URL, the checker typically records:
- final HTTP status code (or a categorized error)
- redirect chain (if any), including intermediate `Location` hops
- timestamps (last checked time)
- latency and retry attempts (if implemented)

Recommended network behavior (to keep runs stable):
- timeouts (connect + read)
- limited redirects (e.g., max 10)
- limited retries for transient failures (DNS, 429, 5xx)
- a descriptive User-Agent (some sites block default clients)
## Report schema: `linkcheck_report.json`

The report is JSON designed to be stable for CI/QA consumption.

A typical top-level shape:
- `generated_at` (ISO-8601 string, UTC recommended)
- `tool` (name/version fields if available)
- `summary` (counts by outcome)
- `results` (list of per-URL records)

Per-URL record fields (recommended/expected):
- `url`: the original URL as found in case-study JSON
- `final_url`: the final URL after redirects (may equal `url`)
- `status`: integer HTTP status code if a response was received
- `ok`: boolean (true for success statuses such as 200–399, per policy)
- `redirects`: list of redirect steps, e.g.:
  - `{ "from": "http://example", "to": "https://example", "status": 301 }`
- `error`: string error category/message when no status is available (DNS, timeout, TLS, blocked, etc.)
- `last_checked_at`: ISO-8601 timestamp of when this URL was checked
- `sources`: list of provenance pointers, e.g.:
  - `{ "case_file": "case_studies/foo.json", "json_path": "$.references[0].url" }`

Notes:
- Some implementations also include `elapsed_ms`, `attempts`, `headers`, or `content_type`.
- If a request fails before an HTTP response, `status` may be omitted/null and `error` populated.
## Summary file: `LINKCHECK_SUMMARY.md`

This Markdown file is intended for humans. Typical contents:
- run timestamp and configuration highlights (timeouts, retries, redirect policy)
- counts: total URLs, OK, redirected, client errors, server errors, network errors
- a short table listing failures (URL, error/status, final URL)
- optionally a section listing redirects that may need link updates
## Interpreting results

Suggested policy conventions:
- OK:
  - 200–299: success
  - 300–399: success if final URL resolves and redirect chain is within limits
- Needs attention:
  - 404/410: broken links (update or remove)
  - 401/403: access controlled (may be expected; consider allowlisting)
  - 429: rate limited (increase backoff or run less frequently)
  - 5xx: server-side issue (often transient)
- Network errors:
  - DNS failure, timeout, TLS handshake issues, connection reset; often transient or environment-specific
## Troubleshooting

1) Timeouts / flaky networks
- Re-run: transient failures often clear.
- Increase timeouts or retries (if CLI supports it).
- Ensure corporate VPN/proxy settings are configured.

2) Redirect loops / too many redirects
- The site may be misconfigured or geofencing.
- Confirm the redirect chain in the report; update the source URL to the stable final URL where appropriate.

3) 403 Forbidden / bot protection
- Some domains block automated clients.
- Use a clear User-Agent; avoid aggressive concurrency.
- If the link is important but blocked, document as “known restricted”.

4) TLS / certificate errors
- System CA store may be outdated.
- Verify you are not intercepting TLS (proxy).
- If running in a locked-down environment, prefer allowing outbound HTTPS with valid certs.

5) Rate limiting (429)
- Reduce concurrency, add backoff, or space checks across runs.

6) CI environment differences
- CI may have no outbound internet; the report will show consistent network errors.
- If needed, gate link-check runs behind an environment flag or run only in approved environments.
## Regenerating outputs

Delete the previous outputs and re-run:
- `runtime/outputs/qa/linkcheck_report.json`
- `runtime/outputs/qa/LINKCHECK_SUMMARY.md`

The runner will recreate both files from the current case-study JSON corpus.

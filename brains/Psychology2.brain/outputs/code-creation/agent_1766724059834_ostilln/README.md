# generated_api_server_1766724060001 — Citation / Primary-Source Access MVP

This project is a lightweight prototype that takes DOI lists and attempts to discover open full-text links across multiple providers (e.g., Unpaywall, OpenAlex, Crossref, PubMed/PMC), returning structured results and writing run artifacts to `outputs/`.

## Quickstart

### 1) Install & run
From the project root (where `src/` exists):

- Create a virtualenv (optional) and install deps:
  - `python -m venv .venv`
  - `source .venv/bin/activate`
  - `pip install -r requirements.txt`

### 2) Configure environment
Some providers work without keys, but Unpaywall requires an email.

Set these environment variables (examples):

- `UNPAYWALL_EMAIL="you@domain.com"` (recommended/required for best results)
- `OPENALEX_EMAIL="you@domain.com"` (optional; polite pool / contact)
- `CROSSREF_MAILTO="you@domain.com"` (optional; improves etiquette/rate limits)
- `NCBI_EMAIL="you@domain.com"` (optional; recommended for NCBI E-utilities)
- `NCBI_API_KEY="..."` (optional; increases NCBI rate limits)

If you do not set these, the system will still attempt discovery with whichever providers are available, but may be rate-limited or receive lower-quality responses.

## Inputs: DOI lists

Accepted input formats:

- Plain text file: one DOI per line (blank lines and `# comments` are ignored)
- JSON file: either `["10....", "10...."]` or `{"dois": ["10....", ...]}`

Example `dois.txt`:
- `10.1038/s41586-020-2649-2`
- `10.1145/3290605.3300233`

## Run the API server (FastAPI)

Start the server (preferred):
- `uvicorn src.api_server:app --host 0.0.0.0 --port 8000`

Then open:
- `http://localhost:8000/docs` (interactive Swagger UI)
- `http://localhost:8000/redoc`

Typical workflow:
1) Submit a DOI list (inline or by providing file contents).
2) Receive a `run_id`.
3) Poll run status and fetch results; artifacts are also written to `outputs/`.

## Run the CLI

The CLI is intended for batch runs against a DOI file and for producing filesystem artifacts in `outputs/`.

Example:
- `python -m src.discovery --doi-file path/to/dois.txt --outdir outputs`

Common options (names may vary slightly by version):
- `--doi-file`: path to `.txt` or `.json` DOI list
- `--outdir`: directory for run outputs (default: `outputs/`)
- `--providers`: optional ordered list like `unpaywall,openalex,crossref,pmc`
- `--max-workers`: concurrency for I/O-bound fetching
- `--timeout`: per-request timeout seconds

## Outputs & logs (written to outputs/)

Each run writes a timestamped or ID-based directory under `outputs/` containing:

- `run_summary.json`: high-level metadata (start/end time, provider order, counts)
- `results.jsonl`: one JSON object per DOI (success/failure + provenance)
- `failures.jsonl`: subset of results where no full text was found
- `http.log` (or similar): request/response diagnostics and provider errors
- `raw/` (optional): provider payload snippets for debugging

### Interpreting per-DOI results
Each DOI outcome is normalized to include:

- `doi`: normalized DOI string
- `status`: e.g., `found_open_fulltext`, `found_metadata_only`, `not_found`, `error`
- `best_fulltext`: the chosen full-text candidate (URL, host, license, type)
- `candidates`: other discovered links (ranked or provider-ordered)
- `provenance`: which provider(s) produced which evidence (Unpaywall/OpenAlex/etc.)
- `errors`: provider errors (timeouts, 429 rate limit, parsing issues), if any

“Success” typically means a stable open full-text URL (PDF/HTML) or a repository landing page (PMC, institutional repository, publisher OA page) with sufficient evidence for retrieval.

## Provider behavior (high level)

- Unpaywall: best for OA status and direct OA URLs (requires email).
- OpenAlex: strong for open-access locations and cross-linking between works.
- Crossref: good metadata; may include resource links but OA coverage varies.
- PubMed/PMC: best for biomedical DOIs; PMC provides stable full text when available.

## Troubleshooting

- If you see many `429` responses: lower concurrency, add emails/API keys, and retry.
- If a DOI repeatedly fails: verify DOI formatting; try without URL prefix; check case.
- If outputs are empty: confirm the server/CLI is writing to the intended `outputs/` path and that the process has write permissions.

## Notes

This MVP focuses on discoverability and provenance logging rather than perfect downloading; downstream steps (e.g., fetching PDFs and content extraction) can be layered on once discovery is reliable.

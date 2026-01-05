# DOI Retriever CLI (doi_retriever.py)

A small CLI tool that takes a list of DOIs, queries a few metadata/availability sources, and writes structured logs of every retrieval attempt (successes and failures). Sources include:
- Unpaywall (OA locations + license when present)
- Crossref (metadata + resource/landing URLs when present)
- Repository/landing-page heuristics (derived URLs; no scraping by default)

The tool is designed for auditability: each DOI can generate multiple attempt records (one per source and/or candidate URL).
## Install / requirements

Python 3.9+.
No special setup is required beyond standard pip dependencies used by the project (see the surrounding repository/package).
## Inputs

You can provide DOIs in any of these ways:
- A text file containing one DOI per line (blank lines and lines starting with `#` are ignored)
- A single DOI via a flag
- A CSV file that includes a `doi` column (the tool will read that column)

DOI normalization: the tool strips surrounding whitespace, removes a leading `doi:` prefix, and tolerates `https://doi.org/` forms.
## Quick start

1) Retrieve for a DOI file and write both JSONL and CSV logs:
    python outputs/tools/doi_retriever.py \
      --input outputs/tools/example_dois.txt \
      --out outputs/tools/run_001 \
      --jsonl --csv \
      --email you@example.com

2) Single DOI:
    python outputs/tools/doi_retriever.py --doi 10.1038/s41586-020-2649-2 --jsonl --out outputs/tools/one

3) Only Unpaywall (fastest):
    python outputs/tools/doi_retriever.py --input my_dois.txt --sources unpaywall --jsonl --out run_unpaywall

4) Crossref + heuristics, no Unpaywall:
    python outputs/tools/doi_retriever.py --input my_dois.txt --sources crossref,heuristics --jsonl --out run_cr
## CLI options (common)

--input PATH
    Path to DOI list file (.txt) or .csv with a `doi` column.

--doi DOI
    Provide a single DOI on the command line (can be used multiple times).

--sources LIST
    Comma-separated sources to query. Default: unpaywall,crossref,heuristics

--out PREFIX
    Output file prefix. Example: `--out outputs/tools/run_001`
    Produces `run_001.attempts.jsonl` and/or `run_001.attempts.csv` depending on flags.

--jsonl / --csv
    Enable JSONL and/or CSV output. You can enable both.

--email EMAIL
    Contact email for polite API usage (recommended; required by some endpoints/policies).

--user-agent UA
    Custom User-Agent string. If omitted, a reasonable default is used.

--timeout SECONDS
    Per-request timeout (default is conservative).

--retries N
    Number of retry attempts for transient failures.

--sleep SECONDS
    Optional delay between requests (basic rate limiting).

--max-dois N
    Process only the first N DOIs after normalization (useful for testing).
## Outputs

The tool writes *attempt logs* (one record per retrieval attempt). A single DOI typically yields multiple records:
- Unpaywall attempt (API call)
- Crossref attempt (API call)
- One or more heuristic URL attempts (derived candidate URLs)

Output formats:
- JSONL: newline-delimited JSON objects (recommended for downstream processing)
- CSV: one row per attempt record (best-effort flattening of nested fields)

Typical output filenames (with `--out outputs/tools/run_001`):
- outputs/tools/run_001.attempts.jsonl
- outputs/tools/run_001.attempts.csv
## Attempt record schema (fields)

Fields may vary slightly by source, but the following are the core fields written in both JSONL and CSV:

Identity / timing
- attempt_id: unique ID for the attempt record
- ts: ISO8601 timestamp of the attempt
- doi: normalized DOI
- source: unpaywall | crossref | heuristics

Request / URL fields
- query_url: URL requested (API endpoint or candidate URL)
- landing_url: landing page URL when discovered (may be same as query_url)
- pdf_url: direct PDF URL when discovered (if any)
- doi_url: canonical https://doi.org/<doi> URL

Outcome fields
- ok: boolean (true if the attempt produced a usable URL or relevant metadata)
- failure_code: short normalized code when ok=false (see below)
- failure_detail: human-readable detail (exception message or API note; may be empty)
- http_status: HTTP status code when applicable
- content_type: response Content-Type when applicable

Open access / license fields (when available)
- is_oa: boolean indicating OA per source (e.g., Unpaywall `is_oa`)
- oa_status: e.g., gold/green/bronze/hybrid (if provided)
- license: license string when provided (e.g., cc-by, cc-by-nc, publisher-specific)
- license_url: URL for license terms when provided
- is_pd: boolean if the source explicitly indicates public domain (rare; usually false/unknown)

Attribution (when available)
- publisher
- journal
- title
- year
- authors (string or list depending on output format)
## Failure codes

Common `failure_code` values:
- invalid_doi: DOI could not be normalized/validated
- http_error: non-2xx response from an HTTP request
- timeout: request timed out
- network_error: DNS/connection/reset errors
- rate_limited: 429 or equivalent backoff condition
- not_found: 404 or source indicates missing record
- no_oa_location: source responded but did not provide any usable OA/URL
- parse_error: unexpected response format / JSON decode error
- blocked: access denied (403) or robot protection detected
- unknown_error: fallback for uncategorized exceptions

Notes:
- For API sources (Unpaywall/Crossref), `http_status` and `failure_detail` are especially useful for debugging.
- For heuristics, failures typically indicate the derived URL was not reachable or did not look like a landing/PDF URL.
## Interpreting results (recommended workflow)

1) Prefer Unpaywall OA locations when present (often includes license and best PDF/landing URL).
2) Fall back to Crossref `link` / `resource` or publisher landing URL.
3) Use heuristics only as a last resort (they are conservative and may produce false positives).

Downstream processing:
- JSONL is easiest to filter/group by DOI and choose the “best” URL based on source priority, license, and presence of pdf_url.
- CSV is convenient for quick inspection and spreadsheet workflows.
## Examples: inspecting logs

Count failures by code:
    python -c "import json; from collections import Counter; c=Counter();\
p='outputs/tools/run_001.attempts.jsonl';\
[ c.update([json.loads(l).get('failure_code')]) for l in open(p,'r',encoding='utf-8') if l.strip() and not json.loads(l).get('ok') ];\
print(c)"

Show best candidate per DOI (simple preference order: unpaywall pdf > unpaywall landing > crossref landing > heuristics):
    python -c "import json;\
pref={'unpaywall':0,'crossref':1,'heuristics':2};\
best={};\
for l in open('outputs/tools/run_001.attempts.jsonl','r',encoding='utf-8'):\
 r=json.loads(l); d=r['doi'];\
 if not r.get('ok'): continue;\
 url=r.get('pdf_url') or r.get('landing_url') or r.get('query_url');\
 key=(pref.get(r.get('source'),9), 0 if r.get('pdf_url') else 1);\
 if d not in best or key<best[d][0]: best[d]=(key,url,r.get('source'));\
print('\n'.join(f"{d}\t{u}\t{s}" for d,(_,u,s) in sorted(best.items())))"

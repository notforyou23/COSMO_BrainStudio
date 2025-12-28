from __future__ import annotations
import os, re, json, time, hashlib, asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = BASE_DIR / "outputs"
RUNS_DIR = OUTPUTS_DIR / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Citation/Full-text Discovery MVP", version="0.1")

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)

class RunRequest(BaseModel):
    dois: List[str] = Field(..., min_length=1)
    providers: Optional[List[str]] = Field(default=None, description="Order: unpaywall, openalex, crossref, pubmed")
    timeout_s: float = 15.0
    max_concurrency: int = 6

class ProviderHit(BaseModel):
    provider: str
    url: Optional[str] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)

class DoiResult(BaseModel):
    doi: str
    ok: bool
    best_url: Optional[str] = None
    hits: List[ProviderHit] = Field(default_factory=list)
    error: Optional[str] = None
    logs: List[str] = Field(default_factory=list)

class RunResponse(BaseModel):
    run_id: str
    created_at: float
    providers: List[str]
    results: List[DoiResult]
    logs: List[str] = Field(default_factory=list)

def _norm_doi(s: str) -> str:
    s = (s or "").strip()
    m = DOI_RE.search(s)
    return m.group(0).lower() if m else s.lower()

def _run_id(dois: List[str], providers: List[str]) -> str:
    payload = {"dois": sorted(_norm_doi(d) for d in dois), "providers": providers}
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"{int(time.time())}_{h}"

async def _get_json(client: httpx.AsyncClient, url: str, headers: Optional[dict]=None, params: Optional[dict]=None) -> Any:
    r = await client.get(url, headers=headers, params=params)
    r.raise_for_status()
    return r.json()

async def _unpaywall(client: httpx.AsyncClient, doi: str, logs: List[str]) -> Optional[ProviderHit]:
    email = os.getenv("UNPAYWALL_EMAIL", "test@example.com")
    url = f"https://api.unpaywall.org/v2/{doi}"
    try:
        j = await _get_json(client, url, params={"email": email})
        best = (j.get("best_oa_location") or {}) if isinstance(j, dict) else {}
        u = best.get("url_for_pdf") or best.get("url")
        if u:
            return ProviderHit(provider="unpaywall", url=u, evidence={"is_oa": j.get("is_oa"), "host_type": best.get("host_type")})
        logs.append("unpaywall:no_url")
    except Exception as e:
        logs.append(f"unpaywall:error:{type(e).__name__}")
    return None

async def _openalex(client: httpx.AsyncClient, doi: str, logs: List[str]) -> Optional[ProviderHit]:
    url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    try:
        j = await _get_json(client, url)
        locs = (((j.get("open_access") or {}) if isinstance(j, dict) else {}).get("oa_url")) or None
        primary = (j.get("primary_location") or {}) if isinstance(j, dict) else {}
        u = primary.get("pdf_url") or primary.get("landing_page_url") or locs
        if u:
            return ProviderHit(provider="openalex", url=u, evidence={"is_oa": (j.get("open_access") or {}).get("is_oa"), "type": j.get("type")})
        logs.append("openalex:no_url")
    except Exception as e:
        logs.append(f"openalex:error:{type(e).__name__}")
    return None

async def _crossref(client: httpx.AsyncClient, doi: str, logs: List[str]) -> Optional[ProviderHit]:
    url = f"https://api.crossref.org/works/{doi}"
    try:
        j = await _get_json(client, url, headers={"User-Agent": "cosmo-mvp/0.1 (mailto:test@example.com)"})
        msg = (j.get("message") or {}) if isinstance(j, dict) else {}
        links = msg.get("link") or []
        if isinstance(links, list):
            for ln in links:
                u = (ln or {}).get("URL")
                if u:
                    return ProviderHit(provider="crossref", url=u, evidence={"content_type": (ln or {}).get("content-type")})
        logs.append("crossref:no_link")
    except Exception as e:
        logs.append(f"crossref:error:{type(e).__name__}")
    return None

async def _pubmed_pmc(client: httpx.AsyncClient, doi: str, logs: List[str]) -> Optional[ProviderHit]:
    try:
        esearch = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        j = await _get_json(client, esearch, params={"db": "pubmed", "retmode": "json", "term": f"{doi}[DOI]"})
        ids = (((j.get("esearchresult") or {}).get("idlist")) or []) if isinstance(j, dict) else []
        if not ids:
            logs.append("pubmed:no_pmid")
            return None
        pmid = ids[0]
        elink = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
        x = await client.get(elink, params={"dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "json"})
        x.raise_for_status()
        lj = x.json()
        linksets = lj.get("linksets") or []
        pmcids = []
        for ls in linksets:
            for db in (ls.get("linksetdbs") or []):
                for lid in (db.get("links") or []):
                    pmcids.append(str(lid))
        if not pmcids:
            logs.append("pubmed:no_pmc")
            return ProviderHit(provider="pubmed", url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", evidence={"pmid": pmid})
        pmcid = pmcids[0]
        return ProviderHit(provider="pmc", url=f"https://pmc.ncbi.nlm.nih.gov/articles/PMC{pmcid}/", evidence={"pmid": pmid, "pmcid": f"PMC{pmcid}"})
    except Exception as e:
        logs.append(f"pubmed:error:{type(e).__name__}")
        return None

PROVIDERS = {
    "unpaywall": _unpaywall,
    "openalex": _openalex,
    "crossref": _crossref,
    "pubmed": _pubmed_pmc,
}

async def _discover_one(doi_in: str, providers: List[str], client: httpx.AsyncClient) -> DoiResult:
    doi = _norm_doi(doi_in)
    logs: List[str] = []
    hits: List[ProviderHit] = []
    if not DOI_RE.match(doi):
        return DoiResult(doi=doi_in, ok=False, error="invalid_doi", logs=["invalid_doi"])
    for p in providers:
        fn = PROVIDERS.get(p)
        if not fn:
            continue
        hit = await fn(client, doi, logs)
        if hit and hit.url:
            hits.append(hit)
            return DoiResult(doi=doi, ok=True, best_url=hit.url, hits=hits, logs=logs)
    return DoiResult(doi=doi, ok=False, hits=hits, error="no_fulltext_found", logs=logs)

def _save_run(resp: RunResponse) -> None:
    p = RUNS_DIR / f"{resp.run_id}.json"
    p.write_text(resp.model_dump_json(indent=2, exclude_none=True), encoding="utf-8")

def _load_run(run_id: str) -> RunResponse:
    p = RUNS_DIR / f"{run_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="run_id_not_found")
    return RunResponse(**json.loads(p.read_text(encoding="utf-8")))

@app.get("/health")
def health() -> dict:
    return {"ok": True}

@app.post("/runs", response_model=RunResponse)
async def create_run(req: RunRequest) -> RunResponse:
    providers = req.providers or ["unpaywall", "openalex", "crossref", "pubmed"]
    providers = [p for p in providers if p in PROVIDERS]
    if not providers:
        raise HTTPException(status_code=400, detail="no_valid_providers")
    run_id = _run_id(req.dois, providers)
    created_at = time.time()
    sem = asyncio.Semaphore(max(1, int(req.max_concurrency)))
    run_logs: List[str] = [f"providers={providers}", f"n_dois={len(req.dois)}"]
    timeout = httpx.Timeout(req.timeout_s)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async def task(d: str) -> DoiResult:
            async with sem:
                return await _discover_one(d, providers, client)
        results = await asyncio.gather(*(task(d) for d in req.dois))
    resp = RunResponse(run_id=run_id, created_at=created_at, providers=providers, results=results, logs=run_logs)
    _save_run(resp)
    return resp

@app.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str) -> RunResponse:
    return _load_run(run_id)

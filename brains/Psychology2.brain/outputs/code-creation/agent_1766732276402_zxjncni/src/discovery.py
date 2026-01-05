from __future__ import annotations
import json, random, time, urllib.parse, urllib.request
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

UA = "generated_api_server_1766724060001/0.1 (mailto:example@example.com)"
DEFAULT_TIMEOUT = 20

def _norm_doi(doi: str) -> str:
    d = (doi or "").strip()
    if d.lower().startswith("https://doi.org/"):
        d = d[16:]
    if d.lower().startswith("http://doi.org/"):
        d = d[15:]
    return d.strip()

def _http_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = DEFAULT_TIMEOUT) -> Any:
    req = urllib.request.Request(url, headers={**({"User-Agent": UA, "Accept": "application/json"}, **(headers or {}))})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return json.loads(data.decode("utf-8", errors="replace"))

def _retry(fn, attempts: int = 4, base: float = 0.7, max_sleep: float = 8.0, retry_on: Tuple[type, ...] = (Exception,)):
    last = None
    for i in range(attempts):
        try:
            return fn()
        except retry_on as e:
            last = e
            sleep = min(max_sleep, base * (2 ** i)) * (0.8 + 0.4 * random.random())
            time.sleep(sleep)
    raise last  # type: ignore[misc]

@dataclass
class Link:
    url: str
    provider: str
    content_type: Optional[str] = None
    is_oa: Optional[bool] = None
    license: Optional[str] = None
    evidence: Optional[str] = None
    version: Optional[str] = None

@dataclass
class DiscoveryResult:
    doi: str
    ok: bool
    best_url: Optional[str]
    links: List[Link]
    errors: List[str]

def _pick_best(links: List[Link]) -> Optional[str]:
    if not links:
        return None
    def score(l: Link) -> Tuple[int, int, int]:
        is_pdf = int((l.content_type or "").lower() == "pdf" or l.url.lower().endswith(".pdf"))
        oa = int(bool(l.is_oa))
        prov = {"unpaywall": 4, "openalex": 3, "pmc": 2, "crossref": 1}.get(l.provider, 0)
        return (is_pdf, oa, prov)
    return sorted(links, key=score, reverse=True)[0].url
def from_unpaywall(doi: str, email: str) -> List[Link]:
    d = _norm_doi(doi)
    if not d or not email:
        return []
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(d)}?email={urllib.parse.quote(email)}"
    j = _retry(lambda: _http_json(url))
    links: List[Link] = []
    best = (j or {}).get("best_oa_location") or {}
    if best.get("url_for_pdf"):
        links.append(Link(best["url_for_pdf"], "unpaywall", content_type="pdf", is_oa=True, license=best.get("license"), evidence="best_oa_location", version=best.get("version")))
    if best.get("url"):
        links.append(Link(best["url"], "unpaywall", is_oa=True, license=best.get("license"), evidence="best_oa_location", version=best.get("version")))
    for loc in (j or {}).get("oa_locations") or []:
        if loc.get("url_for_pdf"):
            links.append(Link(loc["url_for_pdf"], "unpaywall", content_type="pdf", is_oa=True, license=loc.get("license"), evidence="oa_locations", version=loc.get("version")))
        if loc.get("url"):
            links.append(Link(loc["url"], "unpaywall", is_oa=True, license=loc.get("license"), evidence="oa_locations", version=loc.get("version")))
    return _dedupe_links(links)

def from_openalex(doi: str) -> List[Link]:
    d = _norm_doi(doi)
    if not d:
        return []
    url = f"https://api.openalex.org/works/https://doi.org/{urllib.parse.quote(d)}"
    j = _retry(lambda: _http_json(url))
    links: List[Link] = []
    oa = (j or {}).get("open_access") or {}
    primary = (j or {}).get("primary_location") or {}
    pdf = (primary.get("pdf_url") or None)
    if pdf:
        links.append(Link(pdf, "openalex", content_type="pdf", is_oa=bool(oa.get("is_oa")), license=oa.get("oa_status"), evidence="primary_location.pdf_url"))
    landing = primary.get("landing_page_url") or primary.get("source") or None
    if isinstance(landing, str) and landing.startswith("http"):
        links.append(Link(landing, "openalex", is_oa=bool(oa.get("is_oa")), license=oa.get("oa_status"), evidence="primary_location.landing_page_url"))
    for loc in (j or {}).get("locations") or []:
        if loc.get("pdf_url"):
            links.append(Link(loc["pdf_url"], "openalex", content_type="pdf", is_oa=bool(oa.get("is_oa")), license=oa.get("oa_status"), evidence="locations.pdf_url"))
        if loc.get("landing_page_url"):
            links.append(Link(loc["landing_page_url"], "openalex", is_oa=bool(oa.get("is_oa")), license=oa.get("oa_status"), evidence="locations.landing_page_url"))
    return _dedupe_links(links)

def from_crossref(doi: str) -> List[Link]:
    d = _norm_doi(doi)
    if not d:
        return []
    url = f"https://api.crossref.org/works/{urllib.parse.quote(d)}"
    j = _retry(lambda: _http_json(url))
    msg = ((j or {}).get("message") or {})
    links: List[Link] = []
    for l in (msg.get("link") or []):
        u = l.get("URL")
        if not u:
            continue
        ct = (l.get("content-type") or None)
        links.append(Link(u, "crossref", content_type=ct, evidence="message.link"))
    return _dedupe_links(links)
def from_pubmed_pmc(doi: str) -> List[Link]:
    d = _norm_doi(doi)
    if not d:
        return []
    term = urllib.parse.quote(f"{d}[DOI]")
    esearch = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&retmode=json&term={term}"
    sj = _retry(lambda: _http_json(esearch, headers={"Accept": "application/json"}))
    ids = (((sj or {}).get("esearchresult") or {}).get("idlist") or [])
    if not ids:
        return []
    pmid = ids[0]
    elink = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&db=pmc&linkname=pubmed_pmc&retmode=json&id={urllib.parse.quote(str(pmid))}"
    lj = _retry(lambda: _http_json(elink, headers={"Accept": "application/json"}))
    links: List[Link] = []
    for ls in (((lj or {}).get("linksets") or [])):
        for db in (ls.get("linksetdbs") or []):
            for pmc in (db.get("links") or []):
                pmcid = f"PMC{pmc}" if not str(pmc).upper().startswith("PMC") else str(pmc).upper()
                landing = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/"
                pdf = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/"
                links.append(Link(pdf, "pmc", content_type="pdf", is_oa=True, evidence="eutils.elink"))
                links.append(Link(landing, "pmc", is_oa=True, evidence="eutils.elink"))
    return _dedupe_links(links)

def _dedupe_links(links: List[Link]) -> List[Link]:
    seen = set()
    out: List[Link] = []
    for l in links:
        u = (l.url or "").strip()
        if not u:
            continue
        key = u
        if key in seen:
            continue
        seen.add(key)
        out.append(l)
    return out

PROVIDERS = ("unpaywall", "openalex", "crossref", "pmc")

def discover(doi: str, *, email: str = "", provider_order: Tuple[str, ...] = PROVIDERS) -> DiscoveryResult:
    d = _norm_doi(doi)
    links: List[Link] = []
    errors: List[str] = []
    for p in provider_order:
        try:
            if p == "unpaywall":
                links.extend(from_unpaywall(d, email))
            elif p == "openalex":
                links.extend(from_openalex(d))
            elif p == "crossref":
                links.extend(from_crossref(d))
            elif p in ("pmc", "pubmed", "pubmed_pmc"):
                links.extend(from_pubmed_pmc(d))
        except Exception as e:
            errors.append(f"{p}: {type(e).__name__}: {e}")
    links = _dedupe_links(links)
    best = _pick_best(links)
    return DiscoveryResult(doi=d, ok=bool(best), best_url=best, links=links, errors=errors)

def discover_many(dois: List[str], *, email: str = "", provider_order: Tuple[str, ...] = PROVIDERS) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for doi in dois:
        r = discover(doi, email=email, provider_order=provider_order)
        out.append({**asdict(r), "links": [asdict(l) for l in r.links]})
    return out

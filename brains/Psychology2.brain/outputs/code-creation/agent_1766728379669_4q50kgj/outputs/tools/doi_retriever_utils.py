from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

_DOI_RE = re.compile(r"""(?ix)
\b
(?:doi\s*:\s*)?
(10\.[0-9]{4,9}/[^\s"<>]+)
\b
""")

def extract_doi(text: str) -> Optional[str]:
    if not text:
        return None
    m = _DOI_RE.search(text.strip())
    return m.group(1) if m else None

def normalize_doi(doi_or_text: str) -> Optional[str]:
    doi = extract_doi(doi_or_text) or doi_or_text
    if not doi:
        return None
    doi = doi.strip()
    doi = re.sub(r"(?i)^https?://(dx\.)?doi\.org/", "", doi).strip()
    doi = doi.strip().rstrip(".,);]")
    doi = re.sub(r"\s+", "", doi)
    doi = doi.lower()
    return doi if doi.startswith("10.") and "/" in doi else None

def iter_dois(lines: Iterable[str]) -> Iterator[str]:
    for line in lines:
        d = normalize_doi(line)
        if d:
            yield d

def safe_filename(name: str, max_len: int = 180, default: str = "file") -> str:
    if not name:
        name = default
    name = name.strip().replace("\x00", "")
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")
    if not name:
        name = default
    if len(name) > max_len:
        h = hashlib.sha1(name.encode("utf-8")).hexdigest()[:10]
        name = name[: max_len - 11].rstrip(" ._") + "_" + h
    return name

def _jsonable(obj: Any) -> Any:
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonable(x) for x in obj]
    return str(obj)

def write_jsonl(path: Union[str, Path], rows: Iterable[Any], append: bool = False) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with p.open(mode, encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(_jsonable(row), ensure_ascii=False, sort_keys=True) + "\n")

def write_csv(path: Union[str, Path], rows: Sequence[Dict[str, Any]], fieldnames: Optional[List[str]] = None) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys = set()
        for r in rows:
            keys.update(r.keys())
        fieldnames = sorted(keys)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = {}
            for k in fieldnames:
                v = r.get(k)
                if isinstance(v, (dict, list, tuple, set)) or is_dataclass(v):
                    v = json.dumps(_jsonable(v), ensure_ascii=False, sort_keys=True)
                out[k] = "" if v is None else v
            w.writerow(out)

def normalize_url(url: str, drop_query_keys: Optional[Sequence[str]] = ("utm_source","utm_medium","utm_campaign","utm_term","utm_content")) -> Optional[str]:
    if not url:
        return None
    u = url.strip()
    if not u:
        return None
    pr = urlparse(u)
    if pr.scheme and pr.scheme not in ("http", "https"):
        return u
    scheme = pr.scheme or "https"
    netloc = pr.netloc or pr.path
    path = pr.path if pr.netloc else ""
    if not netloc:
        return u
    q = parse_qsl(pr.query, keep_blank_values=True)
    if drop_query_keys:
        drop = {k.lower() for k in drop_query_keys}
        q = [(k, v) for (k, v) in q if k.lower() not in drop]
    query = urlencode(q, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))

def url_host(url: str) -> Optional[str]:
    if not url:
        return None
    try:
        return urlparse(url).netloc.lower() or None
    except Exception:
        return None

def looks_like_pdf_url(url: str) -> bool:
    u = (url or "").lower()
    if ".pdf" in u:
        return True
    return any(s in u for s in ("/pdf/", "?download=1", "download=1", "format=pdf"))

_REPO_HOST_SNIPPETS = (
    "arxiv.org",
    "zenodo.org",
    "biorxiv.org",
    "medrxiv.org",
    "osf.io",
    "ssrn.com",
    "figshare.com",
    "europepmc.org",
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "semanticscholar.org",
)

def host_is_known_repository(host: Optional[str]) -> bool:
    if not host:
        return False
    h = host.lower()
    return any(sn in h for sn in _REPO_HOST_SNIPPETS) or h.startswith("repo.") or h.startswith("eprints.") or h.startswith("dspace.")

def classify_url(url: str) -> str:
    u = (url or "").lower()
    h = url_host(u) or ""
    if looks_like_pdf_url(u):
        return "pdf"
    if "doi.org/" in u or h.endswith("doi.org"):
        return "doi"
    if host_is_known_repository(h):
        return "repository"
    return "landing"

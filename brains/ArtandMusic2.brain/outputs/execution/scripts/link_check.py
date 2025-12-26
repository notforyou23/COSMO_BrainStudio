#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, re, time, sys
from pathlib import Path
from datetime import datetime, timezone

try:
    import requests
except Exception as e:
    requests = None

BASE = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')
IN_QA = BASE/'runtime'/'inputs'/'qa'
OUT_QA = BASE/'runtime'/'outputs'/'qa'
OUT_QA.mkdir(parents=True, exist_ok=True)

URL_RE = re.compile(r'\bhttps?://[^\s)\]}>\"\']+', re.IGNORECASE)

def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def load_config(path: Path) -> dict:
    d = {
        "timeout_s": 15,
        "user_agent": "cosmo-linkcheck/1.0",
        "max_urls": 50,
        "scan_roots": [str(BASE/'runtime'/'inputs')],
        "archive": {"enabled": False, "service": "wayback", "trigger_on_fail": True, "trigger_on_success": False},
    }
    if path and path.exists():
        try:
            d.update(json.loads(path.read_text(encoding='utf-8')))
        except Exception:
            pass
    return d

def read_exemplar_csv(path: Path):
    urls = []
    with path.open('r', encoding='utf-8', newline='') as f:
        r = csv.DictReader(f)
        for row in r:
            u = (row.get('url') or '').strip()
            if u:
                urls.append(u)
    return urls

def find_seed_urls(config: dict) -> list[str]:
    seed = IN_QA/'EXEMPLAR_URLS.csv'
    if seed.exists():
        return read_exemplar_csv(seed)

    # Try media/catalog-like CSVs
    candidates = []
    for root in [BASE/'runtime'/'inputs', BASE/'runtime'/'outputs']:
        if root.exists():
            for p in root.rglob('*.csv'):
                n = p.name.lower()
                if any(k in n for k in ['media', 'catalog', 'catalogue', 'assets', 'links']):
                    candidates.append(p)
    for p in candidates[:5]:
        try:
            text = p.read_text(encoding='utf-8', errors='ignore')
            found = URL_RE.findall(text)
            if found:
                return dedupe(found)[:config.get("max_urls", 50)]
        except Exception:
            continue

    # Extract from pilot case study / markdown/html/text inputs
    scan_paths = []
    for sr in config.get("scan_roots", []):
        pr = Path(sr)
        if pr.exists():
            scan_paths.append(pr)
    files = []
    for pr in scan_paths:
        for ext in ('.md', '.markdown', '.txt', '.html', '.htm', '.json'):
            files.extend(list(pr.rglob(f'*{ext}')))
    files = sorted(files, key=lambda p: (0 if 'pilot' in p.name.lower() else 1, len(str(p))))
    for p in files[:200]:
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        found = URL_RE.findall(txt)
        if found:
            return dedupe(found)[:config.get("max_urls", 50)]

    # Minimal fallback exemplar list
    return ["https://example.com/"]

def dedupe(urls):
    seen, out = set(), []
    for u in urls:
        u = u.strip().rstrip('.,;:)\]\}>\"\'')
        if not u or u in seen:
            continue
        seen.add(u); out.append(u)
    return out

def maybe_archive(url: str, config: dict, ok: bool, session: requests.Session | None):
    pol = (config.get("archive") or {})
    if not pol.get("enabled"):
        return ""
    if ok and not pol.get("trigger_on_success", False):
        return ""
    if (not ok) and not pol.get("trigger_on_fail", True):
        return ""
    svc = (pol.get("service") or "wayback").lower()
    if svc != "wayback" or requests is None or session is None:
        return ""
    try:
        r = session.get("https://web.archive.org/save/" + url, allow_redirects=True, timeout=config.get("timeout_s", 15))
        # Best-effort: use final location if present
        loc = r.headers.get("Content-Location") or r.headers.get("Location") or ""
        if loc.startswith("/"):
            return "https://web.archive.org" + loc
        if loc.startswith("http"):
            return loc
        return ""
    except Exception:
        return ""

def check_url(url: str, config: dict, session: requests.Session | None) -> dict:
    row = {"url": url, "checked_at_utc": utc_now_iso(), "ok": False, "http_status": "", "final_url": "", "error": "", "response_time_s": "", "archived_url": ""}
    if requests is None or session is None:
        row["error"] = "requests_not_available"
        return row
    t0 = time.time()
    headers = {"User-Agent": config.get("user_agent", "cosmo-linkcheck/1.0")}
    timeout = config.get("timeout_s", 15)
    try:
        r = session.head(url, allow_redirects=True, timeout=timeout, headers=headers)
        if r.status_code in (405, 403) or r.status_code >= 500:
            r = session.get(url, allow_redirects=True, timeout=timeout, headers=headers)
        row["http_status"] = str(r.status_code)
        row["final_url"] = r.url or ""
        row["ok"] = 200 <= r.status_code < 400
    except Exception as e:
        row["error"] = (type(e).__name__ + ":" + str(e))[:300]
    row["response_time_s"] = f"{(time.time()-t0):.3f}"
    row["archived_url"] = maybe_archive(url, config, bool(row["ok"]), session)
    return row

def write_report(rows, out_path: Path):
    cols = ["url","ok","http_status","final_url","error","checked_at_utc","response_time_s","archived_url"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})

def main():
    ap = argparse.ArgumentParser(description="Discover exemplar URLs, link-check reachability, and write QA report.")
    ap.add_argument("--config", default=str(IN_QA/'LINKCHECK_CONFIG.json'), help="Path to LINKCHECK_CONFIG.json")
    ap.add_argument("--out", default=str(OUT_QA/'LINK_CHECK_REPORT.csv'), help="Output CSV path")
    ap.add_argument("--max-urls", type=int, default=None, help="Override max URLs")
    args = ap.parse_args()

    config = load_config(Path(args.config) if args.config else None)
    if args.max_urls is not None:
        config["max_urls"] = int(args.max_urls)

    urls = find_seed_urls(config)
    urls = dedupe(urls)[:config.get("max_urls", 50)]

    session = requests.Session() if requests is not None else None
    rows = [check_url(u, config, session) for u in urls]
    write_report(rows, Path(args.out))
    bad = sum(1 for r in rows if not r.get("ok"))
    print(f"WROTE:{args.out} urls={len(rows)} bad={bad}")

if __name__ == "__main__":
    main()

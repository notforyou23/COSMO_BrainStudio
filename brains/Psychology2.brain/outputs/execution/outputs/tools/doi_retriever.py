#!/usr/bin/env python3
import argparse, csv, json, sys, time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def norm_doi(s:str)->str:
    s=(s or '').strip()
    if not s: return ''
    s=s.replace('doi:','').strip()
    if s.lower().startswith('https://doi.org/'): s=s[len('https://doi.org/'):]
    if s.lower().startswith('http://doi.org/'): s=s[len('http://doi.org/'):]
    return s.strip()

def read_dois(path:Path|None):
    if path:
        txt=Path(path).read_text(encoding='utf-8', errors='ignore')
        for line in txt.splitlines():
            d=norm_doi(line)
            if d: yield d
    else:
        for line in sys.stdin:
            d=norm_doi(line)
            if d: yield d

def http_json(url, headers, timeout=20):
    req=Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as r:
            data=r.read().decode('utf-8','replace')
            return r.status, json.loads(data), None
    except HTTPError as e:
        try:
            body=e.read().decode('utf-8','replace')
        except Exception:
            body=''
        return getattr(e,'code',None) or 0, None, f"http_error:{getattr(e,'code',None)}:{body[:200]}"
    except URLError as e:
        return 0, None, f"url_error:{getattr(e,'reason',e)}"
    except Exception as e:
        return 0, None, f"error:{type(e).__name__}:{e}"

def norm_license(s):
    if not s: return None
    s=str(s).strip()
    return s or None

def is_pd_from_license(lic):
    if not lic: return False
    l=lic.lower()
    return ('cc0' in l) or ('public domain' in l) or l.endswith('/zero/1.0') or ('pdm' in l)

@dataclass
class Attempt:
    ts:str
    doi:str
    source:str
    ok:bool
    url:str|None=None
    license:str|None=None
    is_pd:bool|None=None
    status:int|None=None
    error:str|None=None

def write_jsonl(path, rows):
    with open(path,'w',encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(asdict(r), ensure_ascii=False) + '\n')

def write_csv(path, rows):
    cols=['ts','doi','source','ok','url','license','is_pd','status','error']
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            d=asdict(r)
            for c in cols:
                if c not in d: d[c]=None
            w.writerow(d)

def uniq(seq):
    out=[]; seen=set()
    for x in seq:
        if not x: continue
        if x in seen: continue
        seen.add(x); out.append(x)
    return out

def unpaywall(doi, email, headers):
    url=f"https://api.unpaywall.org/v2/{quote(doi)}?{urlencode({'email':email})}"
    st, js, err=http_json(url, headers)
    if err: return Attempt(now_iso(), doi, 'unpaywall', False, status=st, error=err), None
    lic=norm_license(js.get('best_oa_location',{}).get('license')) or norm_license(js.get('license'))
    urls=[]
    bol=js.get('best_oa_location') or {}
    for k in ('url_for_pdf','url'):
        if bol.get(k): urls.append(bol.get(k))
    for loc in (js.get('oa_locations') or []):
        for k in ('url_for_pdf','url'):
            if loc.get(k): urls.append(loc.get(k))
    urls=uniq(urls)
    ok=bool(urls) or bool(js.get('is_oa'))
    a=Attempt(now_iso(), doi, 'unpaywall', ok, url=urls[0] if urls else None, license=lic, is_pd=is_pd_from_license(lic), status=st, error=None if ok else 'no_oa_url')
    return a, {'urls':urls, 'license':lic}

def crossref(doi, headers):
    url=f"https://api.crossref.org/works/{quote(doi)}"
    st, js, err=http_json(url, headers)
    if err: return Attempt(now_iso(), doi, 'crossref', False, status=st, error=err), None
    msg=((js or {}).get('message') or {})
    lic=None
    lics=msg.get('license') or []
    if isinstance(lics,list) and lics:
        lic=norm_license(lics[0].get('URL') or lics[0].get('url') or lics[0].get('content-version'))
    urls=[]
    if msg.get('URL'): urls.append(msg.get('URL'))
    for lk in (msg.get('link') or []):
        if lk.get('URL'): urls.append(lk.get('URL'))
    urls=uniq(urls)
    ok=bool(urls) or lic is not None
    a=Attempt(now_iso(), doi, 'crossref', ok, url=urls[0] if urls else None, license=lic, is_pd=is_pd_from_license(lic), status=st, error=None if ok else 'no_url')
    return a, {'urls':urls, 'license':lic}

def repo_heuristics(doi, seed_urls):
    hosts=('arxiv.org','biorxiv.org','medrxiv.org','zenodo.org','osf.io','europepmc.org','pmc.ncbi.nlm.nih.gov','ssrn.com','hal.science','hal.archives-ouvertes.fr')
    cand=[]
    for u in seed_urls or []:
        try:
            h=u.split('/')[2].lower()
        except Exception:
            continue
        if any(x in h for x in hosts): cand.append(u)
    cand=uniq(cand)
    ok=bool(cand)
    return Attempt(now_iso(), doi, 'repo_heuristics', ok, url=cand[0] if cand else None, license=None, is_pd=None, status=None, error=None if ok else 'no_repo_candidate'), cand

def main():
    ap=argparse.ArgumentParser(description='Query Unpaywall/Crossref and simple repository heuristics for a DOI list; emit attempt logs.')
    ap.add_argument('-i','--input', help='Input file with DOIs (one per line). If omitted, read stdin.')
    ap.add_argument('-o','--out', default='doi_retrieval_log', help='Output base name (no extension).')
    ap.add_argument('--jsonl', help='JSONL output path (default: <out>.jsonl).')
    ap.add_argument('--csv', help='CSV output path (default: <out>.csv).')
    ap.add_argument('--email', default=None, help='Email for Unpaywall (recommended).')
    ap.add_argument('--user-agent', default='doi-retriever/0.1 (+https://example.org)', help='User-Agent header.')
    ap.add_argument('--delay', type=float, default=0.25, help='Delay seconds between external API calls.')
    args=ap.parse_args()

    email=args.email or 'unpaywall@example.org'
    headers={'User-Agent':args.user_agent, 'Accept':'application/json'}
    out_base=Path(args.out)
    jsonl_path=Path(args.jsonl) if args.jsonl else out_base.with_suffix('.jsonl')
    csv_path=Path(args.csv) if args.csv else out_base.with_suffix('.csv')

    attempts=[]
    for doi in read_dois(Path(args.input) if args.input else None):
        a_u, udat = unpaywall(doi, email, headers); attempts.append(a_u); time.sleep(args.delay)
        a_c, cdat = crossref(doi, headers); attempts.append(a_c); time.sleep(args.delay)
        seeds=uniq((udat or {}).get('urls',[]) + (cdat or {}).get('urls',[]))
        a_r, _ = repo_heuristics(doi, seeds); attempts.append(a_r)
    write_jsonl(jsonl_path, attempts)
    write_csv(csv_path, attempts)

if __name__=='__main__':
    main()

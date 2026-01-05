from __future__ import annotations
import json, re, time, uuid, csv, os
from dataclasses import dataclass, asdict
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

ROOT = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')
OUT_CSV = ROOT / 'runtime/_build/tables/doi_results.csv'
OUT_JSON = ROOT / 'runtime/_build/reports/doi_run_report.json'

DOI_TEST_SET = [
    {'doi':'10.1038/nphys1170','notes':'Nature Physics classic; should resolve'},
    {'doi':'10.1145/3368089.3409731','notes':'ACM proceeding; often indexed in Crossref'},
    {'doi':'10.1126/science.169.3946.635','notes':'Science 1970; should resolve'},
    {'doi':'10.5555/THISISNOTAREALDOI','notes':'Intentionally invalid/not found'},
    {'doi':'doi:10.1000/182','notes':'Example DOI format; may not resolve'},
]

_DOI_RE = re.compile(r'^10\.\d{4,9}/\S+$', re.I)

def _now_iso():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def normalize_doi(s: str) -> str:
    s = (s or '').strip()
    s = re.sub(r'^doi:\s*', '', s, flags=re.I)
    s = re.sub(r'^https?://(dx\.)?doi\.org/', '', s, flags=re.I)
    return s.strip()

def is_valid_doi(doi: str) -> bool:
    return bool(_DOI_RE.match(doi or ''))

def _http_json(url: str, headers=None, timeout=15):
    req = Request(url, headers=headers or {'Accept':'application/json','User-Agent':'cosmo-doi-test/1.0'})
    with urlopen(req, timeout=timeout) as r:
        return r.getcode(), json.loads(r.read().decode('utf-8', errors='replace'))

def _crossref(doi: str):
    url = f'https://api.crossref.org/works/{doi}'
    code, data = _http_json(url)
    item = (data or {}).get('message') or {}
    title = (item.get('title') or [''])[0] if isinstance(item.get('title'), list) else (item.get('title') or '')
    year = None
    for key in ('published-print','published-online','issued','created'):
        dp = (item.get(key) or {}).get('date-parts')
        if isinstance(dp, list) and dp and isinstance(dp[0], list) and dp[0]:
            year = dp[0][0]
            break
    return {'provider':'crossref','http_status':code,'title':title,'year':year,'url':item.get('URL')}

def _datacite(doi: str):
    url = f'https://api.datacite.org/dois/{doi}'
    code, data = _http_json(url)
    attr = ((data or {}).get('data') or {}).get('attributes') or {}
    titles = attr.get('titles') or []
    title = ''
    if isinstance(titles, list) and titles:
        title = (titles[0] or {}).get('title') or ''
    year = attr.get('publicationYear')
    urlv = attr.get('url') or (attr.get('doi') and f'https://doi.org/{attr.get("doi")}') or ''
    return {'provider':'datacite','http_status':code,'title':title,'year':year,'url':urlv}

def resolve_doi(doi_raw: str):
    normalized = normalize_doi(doi_raw)
    base = {'doi': doi_raw, 'normalized_doi': normalized, 'ok': False, 'provider': None,
            'status': 'failed', 'reason': None, 'title': '', 'year': None, 'url': '', 'http_status': None}
    if not normalized:
        base.update(reason='invalid_doi:empty')
        return base
    if not is_valid_doi(normalized):
        base.update(reason='invalid_doi:regex_mismatch')
        return base
    providers = [_crossref, _datacite]
    last_err = None
    for fn in providers:
        try:
            r = fn(normalized)
            base.update(provider=r.get('provider'), http_status=r.get('http_status'),
                        title=r.get('title') or '', year=r.get('year'), url=r.get('url') or '')
            base.update(ok=True, status='success', reason='resolved')
            return base
        except HTTPError as e:
            code = getattr(e, 'code', None)
            base.update(provider=getattr(fn, '__name__', 'provider').lstrip('_'), http_status=code)
            if code in (404, 410):
                last_err = f'not_found:http_{code}'
            elif code in (429,):
                last_err = f'rate_limited:http_{code}'
            else:
                last_err = f'http_error:http_{code}'
        except URLError as e:
            last_err = f'network_error:{getattr(e, "reason", e)}'
        except TimeoutError:
            last_err = 'timeout'
        except Exception as e:
            last_err = f'parse_or_unknown_error:{type(e).__name__}'
    base.update(reason=last_err or 'unresolved')
    return base

def write_outputs(results: list[dict], run_id: str, started: str, finished: str):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    cols = ['doi','normalized_doi','ok','provider','status','reason','title','year','url','http_status']
    with OUT_CSV.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in results:
            row = {k: r.get(k) for k in cols}
            w.writerow(row)
    ok_n = sum(1 for r in results if r.get('ok'))
    report = {
        'schema_version': 'doi_run_report_v1',
        'run_id': run_id,
        'started_at': started,
        'finished_at': finished,
        'duration_s': round(max(0.0, time.time() - time.mktime(time.strptime(started, '%Y-%m-%dT%H:%M:%SZ'))), 3),
        'counts': {'total': len(results), 'success': ok_n, 'failure': len(results) - ok_n},
        'results': results,
        'artifacts': {'csv': str(OUT_CSV), 'json': str(OUT_JSON)},
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report

def run_doi_test_set():
    run_id = f'doi_run_{time.strftime("%Y%m%d_%H%M%S", time.gmtime())}_{uuid.uuid4().hex[:8]}'
    started = _now_iso()
    results = []
    for item in DOI_TEST_SET:
        r = resolve_doi(item.get('doi',''))
        r['notes'] = item.get('notes','')
        results.append(r)
    finished = _now_iso()
    report = write_outputs(results, run_id, started, finished)
    return report

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: dict):
        data = (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ('/health', '/'):
            return self._send(200, {'ok': True, 'service': 'api_server', 'time': _now_iso(),
                                    'endpoints': ['/health', '/doi/run'], 'artifacts': {'csv': str(OUT_CSV), 'json': str(OUT_JSON)}})
        if self.path.startswith('/doi/run'):
            try:
                report = run_doi_test_set()
                return self._send(200, report)
            except Exception as e:
                return self._send(500, {'ok': False, 'error': f'{type(e).__name__}: {e}'})
        return self._send(404, {'ok': False, 'error': 'not_found'})

def main():
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '8000'))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f'api_server listening on http://{host}:{port}')
    httpd.serve_forever()

if __name__ == '__main__':
    main()

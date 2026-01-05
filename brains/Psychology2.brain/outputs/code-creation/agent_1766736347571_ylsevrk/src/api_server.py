import json, os, re, sys, time, uuid, logging
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

try:
    import requests
except Exception as e:
    requests = None

DOI_RE = re.compile(r'^10\.[0-9]{4,9}/\S+$', re.I)

FAIL = {
  "OK":"OK",
  "INVALID_INPUT":"INVALID_INPUT",
  "RESOLUTION_FAILED":"RESOLUTION_FAILED",
  "METADATA_FETCH_FAILED":"METADATA_FETCH_FAILED",
  "METADATA_PARSE_FAILED":"METADATA_PARSE_FAILED",
  "NORMALIZATION_FAILED":"NORMALIZATION_FAILED",
  "UNSUPPORTED_ENV":"UNSUPPORTED_ENV",
  "UNKNOWN_ERROR":"UNKNOWN_ERROR",
}

def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")

def _norm_doi(raw):
    if raw is None: return None
    s = str(raw).strip()
    s = re.sub(r'^https?://(dx\.)?doi\.org/', '', s, flags=re.I).strip()
    s = re.sub(r'^doi:\s*', '', s, flags=re.I).strip()
    s = s.strip().strip('.')
    return s

def _json_logger(artifacts_dir, run_id):
    Path(artifacts_dir).mkdir(parents=True, exist_ok=True)
    log_path = Path(artifacts_dir) / "server.log.jsonl"
    logger = logging.getLogger("api_server")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    h = logging.FileHandler(log_path, encoding="utf-8")
    h.setLevel(logging.INFO)
    class J(logging.Formatter):
        def format(self, record):
            base = {"ts": _utc_now(), "level": record.levelname, "run_id": run_id, "msg": record.getMessage()}
            if isinstance(record.args, dict): base.update(record.args)
            return json.dumps(base, ensure_ascii=False)
    h.setFormatter(J())
    logger.addHandler(h)
    logger.propagate = False
    return logger, str(log_path)

def _resolve_doi(doi, timeout=20):
    if not requests:
        return None, FAIL["UNSUPPORTED_ENV"], "requests_missing"
    url = f"https://doi.org/{doi}"
    try:
        r = requests.get(url, allow_redirects=True, timeout=timeout, headers={"User-Agent":"doi-test-server/1.0"})
        if r.status_code >= 400:
            return (r.url or url), FAIL["RESOLUTION_FAILED"], f"http_{r.status_code}"
        return (r.url or url), FAIL["OK"], None
    except Exception as e:
        return url, FAIL["RESOLUTION_FAILED"], e.__class__.__name__

def _fetch_citeproc(doi, timeout=20):
    if not requests:
        return None, FAIL["UNSUPPORTED_ENV"], "requests_missing"
    try:
        h = {"Accept":"application/vnd.citationstyles.csl+json, application/citeproc+json;q=0.9, application/json;q=0.8",
             "User-Agent":"doi-test-server/1.0"}
        r = requests.get(f"https://doi.org/{doi}", headers=h, timeout=timeout)
        if r.status_code >= 400:
            return None, FAIL["METADATA_FETCH_FAILED"], f"http_{r.status_code}"
        try:
            return r.json(), FAIL["OK"], None
        except Exception:
            return None, FAIL["METADATA_PARSE_FAILED"], "non_json"
    except Exception as e:
        return None, FAIL["METADATA_FETCH_FAILED"], e.__class__.__name__

def _fetch_crossref_api(doi, timeout=20):
    if not requests:
        return None, FAIL["UNSUPPORTED_ENV"], "requests_missing"
    try:
        r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=timeout, headers={"User-Agent":"doi-test-server/1.0"})
        if r.status_code >= 400:
            return None, FAIL["METADATA_FETCH_FAILED"], f"http_{r.status_code}"
        try:
            j = r.json()
            return (j.get("message") if isinstance(j, dict) else None), FAIL["OK"], None
        except Exception:
            return None, FAIL["METADATA_PARSE_FAILED"], "non_json"
    except Exception as e:
        return None, FAIL["METADATA_FETCH_FAILED"], e.__class__.__name__

def _first(xs):
    if xs is None: return None
    if isinstance(xs, list) and xs: return xs[0]
    return xs

def _year(meta):
    for k in ("issued","published-print","published-online","created"):
        v = meta.get(k) if isinstance(meta, dict) else None
        try:
            parts = (v.get("date-parts") or [[None]])[0]
            if parts and parts[0]: return int(parts[0])
        except Exception:
            pass
    return None

def _authors(meta):
    a = meta.get("author") if isinstance(meta, dict) else None
    if not isinstance(a, list): return None
    out = []
    for p in a:
        if not isinstance(p, dict): continue
        g, f = p.get("given"), p.get("family")
        name = (" ".join([x for x in [g,f] if x]) or p.get("name") or "").strip()
        if name: out.append(name)
    return out or None

def _normalize(doi, landing_url, accessed_at, meta, parsing_method, failure_reason_code, failure_detail=None):
    rec = {
        "doi": doi,
        "title": _first(meta.get("title")) if isinstance(meta, dict) else None,
        "container_title": _first(meta.get("container-title")) if isinstance(meta, dict) else None,
        "type": meta.get("type") if isinstance(meta, dict) else None,
        "publisher": meta.get("publisher") if isinstance(meta, dict) else None,
        "volume": meta.get("volume") if isinstance(meta, dict) else None,
        "issue": meta.get("issue") if isinstance(meta, dict) else None,
        "page": meta.get("page") if isinstance(meta, dict) else None,
        "issued_year": _year(meta) if isinstance(meta, dict) else None,
        "author": _authors(meta) if isinstance(meta, dict) else None,
        "url": meta.get("URL") if isinstance(meta, dict) else None,
        "provenance": {
            "landing_url": landing_url,
            "accessed_at": accessed_at,
            "parsing_method": parsing_method,
            "failure_reason_code": failure_reason_code,
            "failure_detail": failure_detail,
        }
    }
    return rec

def process_one(raw_doi, timeout=20):
    accessed_at = _utc_now()
    doi = _norm_doi(raw_doi)
    if not doi or not DOI_RE.match(doi):
        return _normalize(doi, None, accessed_at, {}, "input_validation", FAIL["INVALID_INPUT"], "bad_doi")
    landing_url, code, detail = _resolve_doi(doi, timeout=timeout)
    if code != FAIL["OK"]:
        return _normalize(doi, landing_url, accessed_at, {}, "doi_redirect", code, detail)
    meta, code2, detail2 = _fetch_citeproc(doi, timeout=timeout)
    if code2 == FAIL["OK"] and isinstance(meta, dict) and meta:
        return _normalize(doi, landing_url, accessed_at, meta, "doi_content_negotiation_citeproc_json", FAIL["OK"], None)
    meta2, code3, detail3 = _fetch_crossref_api(doi, timeout=timeout)
    if code3 == FAIL["OK"] and isinstance(meta2, dict) and meta2:
        return _normalize(doi, landing_url, accessed_at, meta2, "crossref_api_message", FAIL["OK"], None)
    final_code = code2 if code2 != FAIL["OK"] else code3
    final_detail = detail2 if code2 != FAIL["OK"] else detail3
    return _normalize(doi, landing_url, accessed_at, {}, "metadata_fetch", final_code or FAIL["UNKNOWN_ERROR"], final_detail)

def _send_json(h, status, obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    h.send_response(status)
    h.send_header("Content-Type","application/json; charset=utf-8")
    h.send_header("Content-Length", str(len(data)))
    h.end_headers()
    h.wfile.write(data)

class Handler(BaseHTTPRequestHandler):
    server_version = "DOIAPIServer/1.0"

    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        t0 = time.time()
        try:
            p = urlparse(self.path)
            if p.path == "/health":
                _send_json(self, 200, {"ok": True, "ts": _utc_now(), "run_id": self.server.run_id})
                self.server.logger.info("health", {"path": p.path, "status": 200, "ms": int((time.time()-t0)*1000)})
                return
            if p.path.startswith("/doi/"):
                raw = p.path[len("/doi/"):]
                rec = process_one(raw, timeout=self.server.timeout)
                status = 200 if rec["provenance"]["failure_reason_code"] == FAIL["OK"] else 207
                _send_json(self, status, rec)
                self.server.logger.info("resolve_one", {"path": p.path, "doi": rec.get("doi"), "status": status,
                    "failure_reason_code": rec["provenance"]["failure_reason_code"], "ms": int((time.time()-t0)*1000)})
                return
            _send_json(self, 404, {"error":"not_found"})
        except Exception as e:
            self.server.logger.info("error", {"path": getattr(self, "path", None), "status": 500, "err": e.__class__.__name__})
            _send_json(self, 500, {"error":"internal_error", "type": e.__class__.__name__})

    def do_POST(self):
        t0 = time.time()
        try:
            p = urlparse(self.path)
            if p.path not in ("/resolve", "/v1/resolve"):
                _send_json(self, 404, {"error":"not_found"})
                return
            n = int(self.headers.get("Content-Length","0") or "0")
            body = self.rfile.read(n) if n > 0 else b"{}"
            try:
                payload = json.loads(body.decode("utf-8") or "{}")
            except Exception:
                _send_json(self, 400, {"error":"invalid_json"})
                return
            dois = payload.get("dois") if isinstance(payload, dict) else None
            if isinstance(dois, str): dois = [dois]
            if not isinstance(dois, list) or not dois:
                _send_json(self, 400, {"error":"invalid_input", "expected":{"dois":["10.x/.."]}})
                return
            recs = [process_one(d, timeout=self.server.timeout) for d in dois]
            ok = sum(1 for r in recs if r["provenance"]["failure_reason_code"] == FAIL["OK"])
            _send_json(self, 200, {"run_id": self.server.run_id, "count": len(recs), "ok": ok, "records": recs})
            self.server.logger.info("resolve_batch", {"path": p.path, "status": 200, "count": len(recs), "ok": ok,
                "ms": int((time.time()-t0)*1000)})
        except Exception as e:
            self.server.logger.info("error", {"path": getattr(self, "path", None), "status": 500, "err": e.__class__.__name__})
            _send_json(self, 500, {"error":"internal_error", "type": e.__class__.__name__})

def main():
    host = os.getenv("API_HOST","127.0.0.1")
    port = int(os.getenv("API_PORT","8000"))
    timeout = int(os.getenv("DOI_TIMEOUT","20"))
    artifacts_dir = os.getenv("ARTIFACTS_DIR") or str((Path.cwd() / "artifacts" / ("run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))))
    run_id = os.getenv("RUN_ID") or ("run_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8])
    logger, log_path = _json_logger(artifacts_dir, run_id)
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.run_id, httpd.timeout, httpd.logger, httpd.artifacts_dir, httpd.log_path = run_id, timeout, logger, artifacts_dir, log_path
    logger.info("server_start", {"host": host, "port": port, "timeout": timeout, "artifacts_dir": artifacts_dir, "log_path": log_path})
    print(json.dumps({"run_id": run_id, "host": host, "port": port, "artifacts_dir": artifacts_dir, "log_path": log_path}, ensure_ascii=False))
    httpd.serve_forever()

if __name__ == "__main__":
    main()

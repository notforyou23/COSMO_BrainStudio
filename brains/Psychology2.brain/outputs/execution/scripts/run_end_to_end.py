#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, datetime as dt, json, os, socket, subprocess, sys, time, traceback
from pathlib import Path
from urllib import request, error as urlerror


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = BASE_DIR / "runs"
API_SCRIPT = BASE_DIR / "src" / "api_server.py"


def utc_now_iso():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http_json(method, url, payload=None, headers=None, timeout=30):
    headers = dict(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers.setdefault("Content-Type", "application/json")
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            txt = raw.decode("utf-8", errors="replace")
            if "json" in ctype.lower():
                try:
                    return resp.status, json.loads(txt), txt
                except Exception:
                    return resp.status, None, txt
            try:
                return resp.status, json.loads(txt), txt
            except Exception:
                return resp.status, None, txt
    except urlerror.HTTPError as e:
        raw = e.read() if hasattr(e, "read") else b""
        txt = raw.decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(txt), txt
        except Exception:
            return e.code, None, txt
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


def wait_for_server(base_url, log_fp, deadline_s=45):
    t0 = time.time()
    probes = ["/health", "/healthz", "/status", "/"]
    while time.time() - t0 < deadline_s:
        for p in probes:
            st, js, _ = http_json("GET", base_url + p, timeout=5)
            if st and 200 <= st < 500:
                log_fp.write(f"{utc_now_iso()} server_probe_ok path={p} status={st}\n")
                log_fp.flush()
                return p, st
        time.sleep(0.4)
    raise RuntimeError("API server did not become ready in time")


def curated_doi_test_set():
    # Small, intentionally diverse set: redirects, paywalls, versions/editions, and problematic strings.
    return [
        {"id": "crossref_example_article", "doi": "10.1038/nphys1170", "note": "common article, often resolves via redirects"},
        {"id": "plos_open_access", "doi": "10.1371/journal.pone.0000308", "note": "OA publisher"},
        {"id": "acm_paywallish", "doi": "10.1145/2783446.2783605", "note": "often paywalled"},
        {"id": "springer_redirects", "doi": "10.1007/s00213-011-2501-3", "note": "springer with redirects"},
        {"id": "wiley_redirects", "doi": "10.1002/anie.201410967", "note": "wiley redirect/paywall patterns"},
        {"id": "jstor_paywall", "doi": "10.2307/20024601", "note": "jstor paywall/redirect"},
        {"id": "doi_case_and_prefix", "doi": "DOI:10.1038/NCHEMBIO.1556", "note": "prefix + uppercase DOI"},
        {"id": "doi_url_form", "doi": "https://doi.org/10.1109/5.771073", "note": "URL form"},
        {"id": "bad_format", "doi": "10.0000/NOT_A_REAL_DOI", "note": "expected to fail"},
        {"id": "space_punct", "doi": " 10.1038/nphys1170 ", "note": "leading/trailing whitespace"},
    ]


def extract_field(js, keys):
    cur = js
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def normalize_record(item, status, js, raw_text, endpoint_used, base_url):
    accessed_at = utc_now_iso()
    input_doi = item.get("doi")
    rec = {
        "test_id": item.get("id"),
        "input_doi": input_doi,
        "note": item.get("note"),
        "endpoint_used": endpoint_used,
        "base_url": base_url,
        "accessed_at": accessed_at,
        "http_status": status,
        "ok": bool(status and 200 <= status < 300 and isinstance(js, dict)),
        "failure_reason_code": None,
        "parsing_method": None,
        "landing_url": None,
        "title": None,
        "year": None,
        "authors": None,
        "raw_json": js if isinstance(js, (dict, list)) else None,
        "raw_text": None if isinstance(js, (dict, list)) else raw_text,
    }

    if isinstance(js, dict):
        rec["landing_url"] = js.get("landing_url") or extract_field(js, ["provenance", "landing_url"]) or js.get("url")
        rec["parsing_method"] = js.get("parsing_method") or extract_field(js, ["provenance", "parsing_method"])
        rec["failure_reason_code"] = js.get("failure_reason_code") or extract_field(js, ["provenance", "failure_reason_code"])
        rec["title"] = js.get("title") or extract_field(js, ["normalized", "title"]) or extract_field(js, ["metadata", "title"])
        rec["year"] = js.get("year") or extract_field(js, ["normalized", "year"]) or extract_field(js, ["metadata", "year"]) or extract_field(js, ["issued", "year"])
        rec["authors"] = js.get("authors") or extract_field(js, ["normalized", "authors"]) or extract_field(js, ["metadata", "authors"])

    if not rec["ok"]:
        if rec["failure_reason_code"]:
            pass
        elif status is None:
            rec["failure_reason_code"] = "CLIENT_NETWORK_ERROR"
        elif status == 404:
            rec["failure_reason_code"] = "NOT_FOUND"
        elif status in (401, 403):
            rec["failure_reason_code"] = "PAYWALL_OR_FORBIDDEN"
        elif status >= 500:
            rec["failure_reason_code"] = "SERVER_ERROR"
        else:
            rec["failure_reason_code"] = "UNPARSEABLE_OR_BAD_RESPONSE"
    if not rec["parsing_method"]:
        rec["parsing_method"] = "api_server_response"
    return rec


def choose_endpoints(base_url, doi):
    doi_enc = request.quote(doi.strip())
    return [
        ("POST", "/v1/doi", {"doi": doi}),
        ("POST", "/doi", {"doi": doi}),
        ("POST", "/resolve", {"doi": doi}),
        ("GET", f"/v1/doi/{doi_enc}", None),
        ("GET", f"/doi/{doi_enc}", None),
        ("GET", f"/resolve/{doi_enc}", None),
    ]


def main():
    ap = argparse.ArgumentParser(description="Run api_server.py end-to-end against a curated DOI test set.")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory root for run artifacts.")
    ap.add_argument("--port", type=int, default=0, help="Port to run server on (0 chooses a free port).")
    ap.add_argument("--timeout", type=int, default=45, help="Server readiness timeout seconds.")
    ap.add_argument("--request-timeout", type=int, default=30, help="Per-request timeout seconds.")
    args = ap.parse_args()

    out_root = Path(args.out_dir)
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / f"end_to_end_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    client_log_path = run_dir / "client.log"
    server_log_path = run_dir / "server.log"
    jsonl_path = run_dir / "results.jsonl"
    csv_path = run_dir / "results.csv"
    manifest_path = run_dir / "manifest.json"

    port = args.port or find_free_port()
    base_url = f"http://127.0.0.1:{port}"

    test_set = curated_doi_test_set()
    started_at = utc_now_iso()

    with open(client_log_path, "w", encoding="utf-8") as clog, open(server_log_path, "w", encoding="utf-8") as slog:
        if not API_SCRIPT.exists():
            raise FileNotFoundError(f"Missing {API_SCRIPT}")

        env = os.environ.copy()
        env["PORT"] = str(port)
        env.setdefault("HOST", "127.0.0.1")

        cmd = [sys.executable, "-u", str(API_SCRIPT)]
        clog.write(f"{utc_now_iso()} starting_server cmd={cmd} env_PORT={port}\n")
        clog.flush()

        proc = subprocess.Popen(cmd, cwd=str(BASE_DIR), stdout=slog, stderr=subprocess.STDOUT, env=env)
        endpoint_probe, probe_status = None, None
        try:
            endpoint_probe, probe_status = wait_for_server(base_url, clog, deadline_s=args.timeout)

            results = []
            with open(jsonl_path, "w", encoding="utf-8") as jf:
                for item in test_set:
                    doi = str(item.get("doi", ""))
                    used = None
                    status = None
                    js = None
                    raw = None
                    for method, path, payload in choose_endpoints(base_url, doi):
                        url = base_url + path
                        st, jso, raw_text = http_json(method, url, payload=payload, timeout=args.request_timeout)
                        clog.write(f"{utc_now_iso()} request test_id={item.get('id')} method={method} path={path} status={st}\n")
                        clog.flush()
                        used = f"{method} {path}"
                        status, js, raw = st, jso, raw_text
                        if st and 200 <= st < 300 and isinstance(jso, dict):
                            break
                    rec = normalize_record(item, status, js, raw, used, base_url)
                    results.append(rec)
                    jf.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
                    jf.flush()

            cols = ["test_id","input_doi","note","ok","http_status","failure_reason_code","landing_url","accessed_at","parsing_method","title","year","authors","endpoint_used","base_url"]
            with open(csv_path, "w", encoding="utf-8", newline="") as cf:
                w = csv.DictWriter(cf, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                for r in results:
                    w.writerow(r)

            finished_at = utc_now_iso()
            manifest = {
                "run_id": run_id,
                "started_at": started_at,
                "finished_at": finished_at,
                "base_url": base_url,
                "port": port,
                "server_probe": {"path": endpoint_probe, "status": probe_status},
                "server_cmd": cmd,
                "paths": {
                    "run_dir": str(run_dir),
                    "results_jsonl": str(jsonl_path),
                    "results_csv": str(csv_path),
                    "client_log": str(client_log_path),
                    "server_log": str(server_log_path),
                },
                "test_set": test_set,
                "python": {"executable": sys.executable, "version": sys.version},
            }
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except Exception as e:
            with open(client_log_path, "a", encoding="utf-8") as clog2:
                clog2.write(f"{utc_now_iso()} fatal_error {type(e).__name__}: {e}\n")
                clog2.write(traceback.format_exc() + "\n")
                clog2.flush()
            raise
        finally:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
            except Exception:
                pass

    print(str(manifest_path))


if __name__ == "__main__":
    main()

import csv
import json
import os
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest


REQUIRED_PROV_FIELDS = ("landing_url", "accessed_at", "parsing_method", "failure_reason_code")
ALLOWED_FAILURE_CODES = {
    None,
    "",
    "NONE",
    "INVALID_DOI",
    "RESOLVE_FAILED",
    "REDIRECT_LOOP",
    "TIMEOUT",
    "HTTP_ERROR",
    "NOT_FOUND",
    "PAYWALL",
    "UNSUPPORTED_CONTENT_TYPE",
    "PARSE_ERROR",
    "METADATA_NOT_FOUND",
    "UNKNOWN",
}


def _now_utc_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _extract_provenance(record: dict) -> dict:
    if not isinstance(record, dict):
        return {}
    prov = {}
    if "provenance" in record and isinstance(record["provenance"], dict):
        prov.update(record["provenance"])
    for k in REQUIRED_PROV_FIELDS:
        if k in record:
            prov.setdefault(k, record.get(k))
    return prov


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _poll(url: str, timeout_s: float = 10.0) -> bool:
    import requests
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            r = requests.get(url, timeout=1.5)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _start_server(port: int):
    env = os.environ.copy()
    env["HOST"] = env.get("HOST", "127.0.0.1")
    env["PORT"] = str(port)
    cmd = ["python", "-m", "src.api_server"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    return p


def _stop_server(p):
    if p is None:
        return
    try:
        p.terminate()
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
    except Exception:
        pass


def _requests():
    import requests
    return requests


def _call_api(base: str, doi: str):
    requests = _requests()
    candidates = [
        ("POST", "/v1/resolve", {"doi": doi}),
        ("POST", "/resolve", {"doi": doi}),
        ("POST", "/v1/doi", {"doi": doi}),
        ("GET", f"/v1/doi/{doi}", None),
        ("GET", f"/doi/{doi}", None),
    ]
    last = None
    for method, path, payload in candidates:
        url = base + path
        try:
            if method == "POST":
                r = requests.post(url, json=payload, timeout=20)
            else:
                r = requests.get(url, timeout=20)
            ct = (r.headers.get("content-type") or "").lower()
            if "application/json" in ct or r.status_code in (200, 400, 404, 422):
                try:
                    return r.status_code, r.json(), url
                except Exception:
                    last = (r.status_code, {"raw_text": r.text[:2000]}, url)
        except Exception as e:
            last = (599, {"error": str(e)}, url)
    return last if last is not None else (599, {"error": "no_endpoint_worked"}, base)


@pytest.mark.end_to_end
def test_cli_end_to_end_api_runner_outputs_with_provenance(tmp_path: Path):
    curated = [
        {"doi": "10.1038/nphys1170", "case": "known_article_redirect_possible"},
        {"doi": "10.1109/5.771073", "case": "ieee_paywall_possible"},
        {"doi": "10.1000/182", "case": "multiple_editions_common_demo"},
        {"doi": "10.5555/doesnotexist", "case": "not_found"},
        {"doi": "not_a_doi", "case": "invalid_doi"},
    ]

    port = _find_free_port()
    base = f"http://127.0.0.1:{port}"
    p = _start_server(port)
    try:
        assert _poll(base + "/healthz", timeout_s=15) or _poll(base + "/health", timeout_s=15) or _poll(base + "/", timeout_s=15)

        out_dir = tmp_path / "e2e_run"
        out_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = out_dir / "normalized.jsonl"
        csv_path = out_dir / "normalized.csv"
        log_path = out_dir / "run.log"

        rows = []
        with log_path.open("w", encoding="utf-8") as logf, jsonl_path.open("w", encoding="utf-8") as jf:
            logf.write(f"run_started_at={_now_utc_iso()} base={base}\n")
            for item in curated:
                doi = item["doi"]
                status, payload, endpoint = _call_api(base, doi)
                accessed_at = payload.get("accessed_at") if isinstance(payload, dict) else None
                if not accessed_at:
                    accessed_at = _now_utc_iso()
                record = {
                    "doi": doi,
                    "case": item["case"],
                    "http_status": status,
                    "endpoint": endpoint,
                    "accessed_at": accessed_at,
                    "response": payload,
                }
                jf.write(json.dumps(record, ensure_ascii=False) + "\n")
                logf.write(json.dumps({"doi": doi, "status": status, "endpoint": endpoint}, ensure_ascii=False) + "\n")
                rows.append(record)

        # Build a normalized CSV with stable columns and explicit provenance extraction
        csv_cols = ["doi", "case", "http_status", "endpoint"] + list(REQUIRED_PROV_FIELDS) + ["failure_reason_code_ok"]
        with csv_path.open("w", encoding="utf-8", newline="") as cf:
            w = csv.DictWriter(cf, fieldnames=csv_cols)
            w.writeheader()
            for r in rows:
                prov = _extract_provenance(r.get("response") if isinstance(r, dict) else {})
                failure = prov.get("failure_reason_code")
                ok = failure in ALLOWED_FAILURE_CODES
                w.writerow(
                    {
                        "doi": r.get("doi"),
                        "case": r.get("case"),
                        "http_status": r.get("http_status"),
                        "endpoint": r.get("endpoint"),
                        "landing_url": prov.get("landing_url"),
                        "accessed_at": prov.get("accessed_at") or r.get("accessed_at"),
                        "parsing_method": prov.get("parsing_method"),
                        "failure_reason_code": failure,
                        "failure_reason_code_ok": ok,
                    }
                )

        assert jsonl_path.exists() and jsonl_path.stat().st_size > 0
        assert csv_path.exists() and csv_path.stat().st_size > 0
        assert log_path.exists() and log_path.stat().st_size > 0

        # Assertions: each API response should include required provenance fields either top-level or under "provenance"
        for r in rows:
            payload = r.get("response")
            assert isinstance(payload, dict), f"non-json response for doi={r.get('doi')}: {type(payload)}"
            prov = _extract_provenance(payload)
            missing = [k for k in REQUIRED_PROV_FIELDS if k not in prov]
            assert not missing, f"missing provenance fields for doi={r.get('doi')}: {missing}"
            assert prov.get("failure_reason_code") in ALLOWED_FAILURE_CODES, f"invalid failure_reason_code for doi={r.get('doi')}: {prov.get('failure_reason_code')}"
    finally:
        _stop_server(p)

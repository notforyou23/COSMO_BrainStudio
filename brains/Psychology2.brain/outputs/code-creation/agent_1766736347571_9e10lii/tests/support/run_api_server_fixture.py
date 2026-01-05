from __future__ import annotations
import argparse, csv, json, os, subprocess, sys, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
def _http_json(method: str, url: str, payload: Optional[dict] = None, timeout: float = 20.0) -> Tuple[int, Any, str]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        raw = json.dumps(payload).encode("utf-8")
        data = raw
        headers["Content-Type"] = "application/json"
    req = Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.getcode(), json.loads(body) if body else None, body
            except json.JSONDecodeError:
                return resp.getcode(), None, body
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if getattr(e, "fp", None) else ""
        try:
            parsed = json.loads(body) if body else None
        except json.JSONDecodeError:
            parsed = None
        return e.code, parsed, body
    except URLError as e:
        return 0, None, str(e)
def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def _write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")

def _write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (json.dumps(r.get(k), ensure_ascii=False) if isinstance(r.get(k), (dict, list)) else r.get(k)) for k in fieldnames})
@dataclass
class ServerConfig:
    cmd: List[str]
    base_url: str = "http://127.0.0.1:8000"
    ready_paths: Tuple[str, ...] = ("/health", "/docs", "/")
    start_timeout_s: float = 45.0
    request_timeout_s: float = 30.0
    env: Optional[Dict[str, str]] = None
    cwd: Optional[Path] = None
def start_server(cfg: ServerConfig) -> subprocess.Popen:
    env = os.environ.copy()
    if cfg.env:
        env.update(cfg.env)
    p = subprocess.Popen(
        cfg.cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        cwd=str(cfg.cwd) if cfg.cwd else None,
    )
    start = time.time()
    last_out = ""
    while time.time() - start < cfg.start_timeout_s:
        if p.poll() is not None:
            out = p.stdout.read() if p.stdout else ""
            raise RuntimeError(f"server exited early rc={p.returncode}:\n{out[-4000:]}")
        if p.stdout:
            try:
                while True:
                    line = p.stdout.readline()
                    if not line:
                        break
                    last_out = (last_out + line)[-4000:]
            except Exception:
                pass
        for rp in cfg.ready_paths:
            code, _, _ = _http_json("GET", cfg.base_url + rp, None, timeout=5.0)
            if code:
                return p
        time.sleep(0.25)
    raise TimeoutError(f"server not ready after {cfg.start_timeout_s}s; last_output_tail=\n{last_out}")
def stop_server(p: subprocess.Popen, timeout_s: float = 10.0) -> None:
    if p.poll() is not None:
        return
    try:
        p.terminate()
        p.wait(timeout=timeout_s)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass
def run_cli(cli_cmd: List[str], doi: str, timeout_s: float = 45.0, cwd: Optional[Path] = None) -> Dict[str, Any]:
    p = subprocess.run(cli_cmd + [doi], capture_output=True, text=True, timeout=timeout_s, cwd=str(cwd) if cwd else None)
    out = (p.stdout or "").strip()
    err = (p.stderr or "").strip()
    parsed = None
    if out:
        try:
            parsed = json.loads(out)
        except Exception:
            parsed = None
    ok = (p.returncode == 0) and (parsed is not None or out != "")
    return {"ok": ok, "returncode": p.returncode, "stdout": out, "stderr": err, "json": parsed}
def run_server_request(base_url: str, endpoint: str, doi: str, timeout_s: float = 30.0) -> Dict[str, Any]:
    url = base_url.rstrip("/") + "/" + endpoint.lstrip("/")
    code, parsed, raw = _http_json("POST", url, {"doi": doi}, timeout=timeout_s)
    ok = (200 <= code < 300) and (parsed is not None or raw != "")
    return {"ok": ok, "http_status": code, "json": parsed, "raw": raw}
def run_fixtures(
    fixtures: List[Dict[str, Any]],
    mode: str,
    output_dir: Path,
    *,
    server: Optional[ServerConfig] = None,
    server_endpoint: str = "/doi",
    cli_cmd: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
) -> Dict[str, Any]:
    _ensure_dir(output_dir)
    results: List[Dict[str, Any]] = []
    server_proc: Optional[subprocess.Popen] = None
    try:
        if mode == "server":
            if not server:
                raise ValueError("server config required for mode=server")
            server_proc = start_server(server)
        for fx in fixtures:
            doi = fx.get("doi") or fx.get("DOI")
            if not doi:
                results.append({"doi": None, "ok": False, "error": "missing_doi", "fixture": fx})
                continue
            expected = fx.get("expected", fx.get("expect"))
            expect_ok = True if expected is None else bool(expected.get("ok", expected.get("success", True)) if isinstance(expected, dict) else bool(expected))
            t0 = time.time()
            if mode == "cli":
                if not cli_cmd:
                    raise ValueError("cli_cmd required for mode=cli")
                r = run_cli(cli_cmd, doi, cwd=cwd)
            elif mode == "server":
                r = run_server_request(server.base_url, server_endpoint, doi, timeout_s=server.request_timeout_s)
            else:
                raise ValueError(f"unknown mode: {mode}")
            dt_ms = int((time.time() - t0) * 1000)
            got_ok = bool(r.get("ok"))
            results.append({
                "doi": doi,
                "expect_ok": expect_ok,
                "got_ok": got_ok,
                "status": "PASS" if got_ok == expect_ok else "FAIL",
                "elapsed_ms": dt_ms,
                "fixture": fx,
                "result": r,
            })
    finally:
        if server_proc is not None:
            stop_server(server_proc)
    summary = {"total": len(results), "pass": sum(1 for r in results if r["status"] == "PASS"), "fail": sum(1 for r in results if r["status"] == "FAIL")}
    payload = {"summary": summary, "mode": mode, "results": results}
    _write_json(output_dir / "doi_fixture_results.json", payload)
    _write_csv(
        output_dir / "doi_fixture_results.csv",
        results,
        fieldnames=["doi", "expect_ok", "got_ok", "status", "elapsed_ms"],
    )
    return payload
def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Run DOI fixtures against api_server (server mode) or CLI (cli mode).")
    ap.add_argument("--fixtures", required=True, help="Path to fixtures JSON (list of dicts, each containing 'doi').")
    ap.add_argument("--output-dir", required=True, help="Directory for artifacts (JSON/CSV).")
    ap.add_argument("--mode", choices=["server", "cli"], required=True)
    ap.add_argument("--server-cmd", default="", help="Server command as a single shell-like string (e.g. 'python api_server.py').")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--endpoint", default="/doi", help="POST endpoint for DOI requests in server mode.")
    ap.add_argument("--cli-cmd", default="", help="CLI command as a single shell-like string (e.g. 'python -m tool.cli'). DOI appended as final arg.")
    ap.add_argument("--cwd", default="", help="Working directory for subprocesses.")
    return ap.parse_args(argv)

def _split_cmd(s: str) -> List[str]:
    if not s.strip():
        return []
    import shlex
    return shlex.split(s)
def main(argv: Optional[List[str]] = None) -> int:
    ns = _parse_args(argv)
    fixtures_path = Path(ns.fixtures)
    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
    if not isinstance(fixtures, list):
        raise ValueError("fixtures JSON must be a list")
    out_dir = Path(ns.output_dir)
    cwd = Path(ns.cwd) if ns.cwd else None
    server_cfg = None
    cli_cmd = None
    if ns.mode == "server":
        cmd = _split_cmd(ns.server_cmd)
        if not cmd:
            raise ValueError("--server-cmd required for mode=server")
        server_cfg = ServerConfig(cmd=cmd, base_url=ns.base_url, cwd=cwd)
    else:
        cli_cmd = _split_cmd(ns.cli_cmd)
        if not cli_cmd:
            raise ValueError("--cli-cmd required for mode=cli")
    payload = run_fixtures(fixtures, ns.mode, out_dir, server=server_cfg, server_endpoint=ns.endpoint, cli_cmd=cli_cmd, cwd=cwd)
    return 0 if payload["summary"]["fail"] == 0 else 2

if __name__ == "__main__":
    raise SystemExit(main())

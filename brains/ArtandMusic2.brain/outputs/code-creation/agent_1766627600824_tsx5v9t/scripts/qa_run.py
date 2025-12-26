#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, time, re, hashlib, subprocess
from pathlib import Path

EXIT = {"PASS": 0, "WARN": 0, "FAIL": 1, "ERROR": 2}
ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "outputs"
QA_DIR = OUT_DIR / "qa"
REPORT_PATH = QA_DIR / "QA_REPORT.json"
LOG_PATH = QA_DIR / "qa_run.log"

def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _ensure_dirs():
    QA_DIR.mkdir(parents=True, exist_ok=True)

def _atomic_write_json(path: Path, payload: dict):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def _append_log(msg: str):
    _ensure_dirs()
    LOG_PATH.open("a", encoding="utf-8").write(msg.rstrip() + "\n")

def _run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=timeout)
        return p.returncode, p.stdout or ""
    except Exception as e:
        return 999, f"{type(e).__name__}: {e}"

def _docker_available() -> tuple[bool, str]:
    rc, out = _run(["docker", "version"], timeout=20)
    if rc != 0:
        return False, out.strip() or "docker not available"
    rc, out2 = _run(["docker", "info"], timeout=25)
    if rc != 0:
        return False, out2.strip() or "docker daemon unavailable"
    return True, "docker ok"

def _hash_tree(root: Path, limit: int = 2000) -> str:
    h = hashlib.sha256()
    n = 0
    for p in sorted(root.rglob("*")):
        if n >= limit:
            break
        if p.is_file():
            rel = str(p.relative_to(root)).encode()
            h.update(rel)
            try:
                st = p.stat()
                h.update(str(st.st_size).encode())
                h.update(str(int(st.st_mtime)).encode())
            except Exception:
                pass
            n += 1
    return h.hexdigest()

def _validate_json_file(p: Path) -> tuple[bool, str]:
    try:
        json.loads(p.read_text(encoding="utf-8"))
        return True, ""
    except Exception as e:
        return False, f"invalid json: {type(e).__name__}: {e}"

def _schema_validate(instance: object, schema: dict) -> tuple[bool, str]:
    # Pure-python minimal JSON Schema subset: type/object/required/properties/items/enum
    def bad(msg): return (False, msg)
    def ok(): return (True, "")
    st = schema.get("type")
    if st == "object":
        if not isinstance(instance, dict): return bad("expected object")
        req = schema.get("required", [])
        for k in req:
            if k not in instance: return bad(f"missing required: {k}")
        props = schema.get("properties", {})
        for k, sch in props.items():
            if k in instance:
                v = instance[k]
                r, m = _schema_validate(v, sch)
                if not r: return bad(f"{k}: {m}")
        return ok()
    if st == "array":
        if not isinstance(instance, list): return bad("expected array")
        item_s = schema.get("items")
        if item_s:
            for i, v in enumerate(instance[:1000]):
                r, m = _schema_validate(v, item_s)
                if not r: return bad(f"items[{i}]: {m}")
        return ok()
    if st == "string":
        if not isinstance(instance, str): return bad("expected string")
    elif st == "number":
        if not isinstance(instance, (int, float)): return bad("expected number")
    elif st == "integer":
        if not isinstance(instance, int): return bad("expected integer")
    elif st == "boolean":
        if not isinstance(instance, bool): return bad("expected boolean")
    elif st == "null":
        if instance is not None: return bad("expected null")
    if "enum" in schema and instance not in schema["enum"]:
        return bad("not in enum")
    return ok()

def _linkcheck(paths: list[Path], timeout: float = 5.0, limit: int = 50) -> tuple[str, list[dict]]:
    if not paths:
        return "skipped", []
    try:
        import urllib.request
    except Exception:
        return "skipped", [{"severity":"warn","message":"urllib unavailable for linkcheck"}]
    url_re = re.compile(r"https?://[^\s)\]>\"']+")
    findings = []
    checked = 0
    for p in paths:
        if checked >= limit: break
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for url in url_re.findall(txt):
            if checked >= limit: break
            checked += 1
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent":"qa-runner/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    code = getattr(resp, "status", 200)
                if int(code) >= 400:
                    findings.append({"severity":"fail","message":f"bad link {url} -> {code}","path":str(p)})
            except Exception as e:
                findings.append({"severity":"warn","message":f"linkcheck error {url}: {type(e).__name__}","path":str(p)})
    return "ran", findings

def _failsafe_checks(enable_linkcheck: bool) -> dict:
    findings = []
    if not OUT_DIR.exists():
        findings.append({"severity":"fail","message":"outputs directory missing","path":str(OUT_DIR)})
        return {"mode":"failsafe","checks":[], "findings":findings}
    expected = os.environ.get("QA_EXPECTED_FILES")
    if expected:
        try:
            exp = json.loads(expected)
            if isinstance(exp, list):
                for rel in exp:
                    p = ROOT / str(rel)
                    if not p.exists():
                        findings.append({"severity":"fail","message":"missing expected file","path":str(p)})
            else:
                findings.append({"severity":"warn","message":"QA_EXPECTED_FILES not a JSON list"})
        except Exception as e:
            findings.append({"severity":"warn","message":f"QA_EXPECTED_FILES parse error: {type(e).__name__}"})
    json_paths = [p for p in OUT_DIR.rglob("*.json") if QA_DIR not in p.parents]
    bad_json = 0
    for p in sorted(json_paths)[:200]:
        ok, msg = _validate_json_file(p)
        if not ok:
            bad_json += 1
            findings.append({"severity":"fail","message":msg,"path":str(p)})
    schema_path = os.environ.get("QA_SCHEMA_PATH")
    if schema_path:
        sp = ROOT / schema_path
        if sp.exists():
            try:
                schema = json.loads(sp.read_text(encoding="utf-8"))
                target = os.environ.get("QA_SCHEMA_TARGET")
                tp = (ROOT / target) if target else None
                if tp and tp.exists():
                    inst = json.loads(tp.read_text(encoding="utf-8"))
                    ok, msg = _schema_validate(inst, schema)
                    if not ok:
                        findings.append({"severity":"fail","message":f"schema validation failed: {msg}","path":str(tp)})
                else:
                    findings.append({"severity":"warn","message":"QA_SCHEMA_TARGET not set or missing; schema loaded but not applied","path":str(sp)})
            except Exception as e:
                findings.append({"severity":"warn","message":f"schema load/validate error: {type(e).__name__}: {e}","path":str(sp)})
        else:
            findings.append({"severity":"warn","message":"QA_SCHEMA_PATH missing","path":str(sp)})
    md_paths = [p for p in OUT_DIR.rglob("*.md") if QA_DIR not in p.parents]
    if enable_linkcheck:
        status, lf = _linkcheck(sorted(md_paths)[:50])
        findings.extend(lf)
    checks = [
        {"name":"outputs_exists","status":"pass" if OUT_DIR.exists() else "fail"},
        {"name":"json_parseability","status":"pass" if bad_json == 0 else "fail","details":{"scanned":min(len(json_paths),200),"bad":bad_json}},
        {"name":"linkcheck","status":"skipped" if not enable_linkcheck else "done"},
    ]
    return {"mode":"failsafe","checks":checks,"findings":findings}

def _docker_run() -> tuple[bool, dict, str]:
    image = os.environ.get("QA_DOCKER_IMAGE")
    if not image:
        return False, {}, "QA_DOCKER_IMAGE not set"
    cmd = ["docker","run","--rm","-v",f"{ROOT}:/work","-w","/work",image,"python","-m","scripts.qa_run_in_container"]
    rc, out = _run(cmd, timeout=int(os.environ.get("QA_DOCKER_TIMEOUT","900")))
    if rc != 0:
        return False, {}, out.strip() or f"docker run failed rc={rc}"
    # Expect container to write outputs/qa/QA_REPORT.json; if not, treat as failure for fallback.
    if not REPORT_PATH.exists():
        return False, {}, "docker completed but QA_REPORT.json missing"
    try:
        payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return False, {}, f"docker report unreadable: {type(e).__name__}: {e}"
    return True, payload, out

def _summarize_status(findings: list[dict]) -> str:
    sev = [f.get("severity","") for f in findings]
    if "fail" in sev: return "FAIL"
    if "error" in sev: return "ERROR"
    if "warn" in sev: return "WARN"
    return "PASS"

def main(argv: list[str]) -> int:
    _ensure_dirs()
    enable_linkcheck = ("--linkcheck" in argv) or (os.environ.get("QA_LINKCHECK","0") == "1")
    force_no_docker = ("--no-docker" in argv) or (os.environ.get("QA_NO_DOCKER","0") == "1")
    started = _now_iso()
    run_meta = {"started_at": started, "root": str(ROOT), "outputs": str(OUT_DIR), "tree_hash": _hash_tree(OUT_DIR) if OUT_DIR.exists() else None}
    _append_log(f"[{started}] qa_run start force_no_docker={force_no_docker} linkcheck={enable_linkcheck}")
    used = "failsafe"
    docker_note = ""
    payload = None
    if not force_no_docker:
        ok, note = _docker_available()
        docker_note = note
        _append_log(f"[{_now_iso()}] docker availability: {ok} ({note})")
        if ok:
            d_ok, d_payload, d_out = _docker_run()
            _append_log(f"[{_now_iso()}] docker run ok={d_ok}")
            if d_out:
                _append_log(d_out[-4000:])
            if d_ok:
                used = "docker"
                payload = d_payload
    if payload is None:
        payload = _failsafe_checks(enable_linkcheck=enable_linkcheck)
    payload.setdefault("mode", used)
    payload.setdefault("run_meta", {})
    payload["run_meta"].update(run_meta)
    payload["run_meta"]["docker_note"] = docker_note
    payload["run_meta"]["finished_at"] = _now_iso()
    findings = payload.get("findings", [])
    status = payload.get("status") or _summarize_status(findings)
    payload["status"] = status
    _atomic_write_json(REPORT_PATH, payload)
    _append_log(f"[{_now_iso()}] qa_run finished status={status} mode={used} report={REPORT_PATH}")
    return EXIT.get(status, 2)

if __name__ == "__main__":
    try:
        code = main(sys.argv[1:])
    except SystemExit as e:
        code = int(getattr(e, "code", 2) or 2)
    except Exception as e:
        _ensure_dirs()
        payload = {"mode":"failsafe","status":"ERROR","findings":[{"severity":"error","message":f"uncaught: {type(e).__name__}: {e}"}],"run_meta":{"started_at":_now_iso(),"finished_at":_now_iso()}}
        try: _atomic_write_json(REPORT_PATH, payload)
        except Exception: pass
        try: _append_log(f"[{_now_iso()}] uncaught exception: {type(e).__name__}: {e}")
        except Exception: pass
        code = 2
    raise SystemExit(code)

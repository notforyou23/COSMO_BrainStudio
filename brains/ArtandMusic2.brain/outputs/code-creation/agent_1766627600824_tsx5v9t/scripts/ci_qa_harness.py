#!/usr/bin/env python3
import os, sys, json, shlex, subprocess, time
from pathlib import Path

REPO_ROOT = Path(os.getcwd()).resolve()
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "qa_harness.json"

def _load_config():
    cfg = {}
    if DEFAULT_CONFIG_PATH.is_file():
        cfg = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    outputs_root = Path(cfg.get("outputs_root", "outputs"))
    report_path = Path(cfg.get("report_path", str(outputs_root / "QA_REPORT.json")))
    qa_cmd = cfg.get("qa_command") or cfg.get("qa_cmd") or ["python", "-m", "pytest", "-q"]
    if isinstance(qa_cmd, str):
        qa_cmd = shlex.split(qa_cmd)
    allow_paths = [Path(p) for p in (cfg.get("allow_write_paths") or [])]
    allow_globs = list(cfg.get("allow_write_globs") or [])
    ignore_globs = list(cfg.get("ignore_globs") or [".git/**", str(outputs_root / "**")])
    max_log_chars = int(cfg.get("max_log_chars", 20000))
    return {
        "outputs_root": outputs_root,
        "report_path": report_path,
        "qa_cmd": qa_cmd,
        "allow_paths": allow_paths,
        "allow_globs": allow_globs,
        "ignore_globs": ignore_globs,
        "max_log_chars": max_log_chars,
    }

def _scaffold_outputs(outputs_root: Path, report_path: Path):
    out = (REPO_ROOT / outputs_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / ".gitkeep").write_text("", encoding="utf-8")
    rp = (REPO_ROOT / report_path).resolve()
    rp.parent.mkdir(parents=True, exist_ok=True)
    return out, rp

def _is_ignored(rel: str, ignore_globs):
    p = Path(rel)
    for g in ignore_globs:
        if p.match(g):
            return True
    return False

def _snapshot_tree(ignore_globs):
    snap = {}
    for p in REPO_ROOT.rglob("*"):
        try:
            if p.is_symlink() or (not p.is_file()):
                continue
            rel = str(p.relative_to(REPO_ROOT))
            if _is_ignored(rel, ignore_globs):
                continue
            st = p.stat()
            snap[rel] = (st.st_size, getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
        except (OSError, ValueError):
            continue
    return snap

def _is_allowed(rel: str, outputs_root: Path, allow_paths, allow_globs):
    r = Path(rel)
    if r.parts and r.parts[0] == str(outputs_root):
        return True
    for ap in allow_paths:
        try:
            ap_rel = ap if ap.is_absolute() else ap
            if r == ap_rel or str(r).startswith(str(ap_rel).rstrip("/") + "/"):
                return True
        except Exception:
            pass
    for g in allow_globs:
        if r.match(g):
            return True
    return False

def _validate_writes(before, after, outputs_root: Path, allow_paths, allow_globs):
    violations = []
    for rel, meta in after.items():
        if not _is_allowed(rel, outputs_root, allow_paths, allow_globs):
            if rel not in before:
                violations.append({"path": rel, "reason": "created"})
            elif before[rel] != meta:
                violations.append({"path": rel, "reason": "modified"})
    return violations

def _run(cmd):
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), capture_output=True, text=True)
    t1 = time.time()
    return proc, t1 - t0

def main():
    cfg = _load_config()
    outputs_root, report_path = cfg["outputs_root"], cfg["report_path"]
    out_dir, report_file = _scaffold_outputs(outputs_root, report_path)

    before = _snapshot_tree(cfg["ignore_globs"])
    proc, elapsed = _run(cfg["qa_cmd"])
    after = _snapshot_tree(cfg["ignore_globs"])

    violations = _validate_writes(before, after, outputs_root, cfg["allow_paths"], cfg["allow_globs"])
    qa_ok = (proc.returncode == 0)
    policy_ok = (len(violations) == 0)
    ok = qa_ok and policy_ok

    def trunc(s):
        s = s or ""
        m = cfg["max_log_chars"]
        return s if len(s) <= m else (s[:m] + f"\n...[truncated {len(s)-m} chars]")

    report = {
        "ok": ok,
        "qa": {
            "cmd": cfg["qa_cmd"],
            "returncode": proc.returncode,
            "elapsed_seconds": round(elapsed, 3),
            "stdout": trunc(proc.stdout),
            "stderr": trunc(proc.stderr),
        },
        "write_policy": {
            "outputs_root": str(outputs_root),
            "violations": violations,
        },
        "paths": {
            "repo_root": str(REPO_ROOT),
            "outputs_dir": str(out_dir),
            "report_file": str(report_file),
        },
    }
    report_file.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"QA_REPORT_WRITTEN:{report_file}")
    if not qa_ok:
        print("QA_GATE:FAIL")
    if not policy_ok:
        print(f"WRITE_POLICY:FAIL:{len(violations)}_violation(s)")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())

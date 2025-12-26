#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json, os, sys, subprocess, shlex
from datetime import datetime

REQUIRED = [
    "REPORT_OUTLINE.md",
    "CASE_STUDY_TEMPLATE.md",
    "METADATA_SCHEMA.md",
    "CASE_STUDIES_INDEX.csv",
]
RIGHTS_CANDIDATES = [
    "RIGHTS.md","RIGHTS.txt","RIGHTS.json","LICENSE","LICENSE.txt","LICENSE.md",
    "NOTICE","NOTICE.txt","NOTICE.md","COPYRIGHT","COPYRIGHT.txt","COPYRIGHT.md",
]
RIGHTS_GLOBS = ["*RIGHTS*","*LICENSE*","*NOTICE*","*COPYRIGHT*"]

def find_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(10):
        if (cur / "outputs").exists() or (cur / "pyproject.toml").exists() or (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.resolve()

def run(cmd: str, cwd: Path, timeout: int = 120) -> dict:
    p = subprocess.run(
        shlex.split(cmd),
        cwd=str(cwd),
        env=dict(os.environ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    return {"cmd": cmd, "returncode": p.returncode, "stdout": p.stdout[-20000:], "stderr": p.stderr[-20000:]}

def pick_generator_cmd(root: Path) -> str | None:
    candidates = []
    if (root / "scripts" / "generate_scaffold.py").is_file():
        candidates.append(f"{sys.executable} scripts/generate_scaffold.py")
    if (root / "scripts" / "scaffold_generator.py").is_file():
        candidates.append(f"{sys.executable} scripts/scaffold_generator.py")
    if (root / "scripts" / "generate.py").is_file():
        candidates.append(f"{sys.executable} scripts/generate.py")
    if (root / "src").is_dir():
        candidates.append(f"{sys.executable} -m scaffold_generator")
        candidates.append(f"{sys.executable} -m src.scaffold_generator")
        candidates.append(f"{sys.executable} -m src.scaffold.generate")
    for c in candidates:
        return c
    return None

def check_outputs(outputs: Path) -> dict:
    res = {"required": {}, "rights": {"found": [], "ok": False}, "ok": False}
    for name in REQUIRED:
        p = outputs / name
        res["required"][name] = {"path": str(p), "exists": p.is_file(), "size": p.stat().st_size if p.is_file() else 0}
    found = set()
    for n in RIGHTS_CANDIDATES:
        p = outputs / n
        if p.is_file():
            found.add(p.name)
    for g in RIGHTS_GLOBS:
        for p in outputs.glob(g):
            if p.is_file():
                found.add(p.name)
    res["rights"]["found"] = sorted(found)
    res["rights"]["ok"] = len(found) > 0
    res["ok"] = all(v["exists"] for v in res["required"].values()) and res["rights"]["ok"]
    return res

def write_reports(qa_dir: Path, payload: dict) -> tuple[Path, Path]:
    qa_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    jpath = qa_dir / f"validate_scaffold_{stamp}.json"
    tpath = qa_dir / f"validate_scaffold_{stamp}.txt"
    jpath.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    lines = []
    lines.append(f"validate_scaffold: {'PASS' if payload['ok'] else 'FAIL'}")
    lines.append(f"root: {payload['root']}")
    lines.append(f"outputs: {payload['outputs']}")
    if payload.get("generator"):
        lines.append(f"generator: {payload['generator'].get('cmd','')}")
        lines.append(f"generator_rc: {payload['generator'].get('returncode')}")
    lines.append("required_files:")
    for k, v in payload["checks"]["required"].items():
        lines.append(f"  - {k}: {'OK' if v['exists'] else 'MISSING'} ({v['size']} bytes)")
    rf = payload["checks"]["rights"]
    lines.append(f"rights_artifacts: {'OK' if rf['ok'] else 'MISSING'}; found={', '.join(rf['found']) if rf['found'] else '(none)'}")
    if payload.get("generator") and payload["generator"].get("returncode", 0) != 0:
        lines.append("generator_stderr_tail:")
        lines.append(payload["generator"].get("stderr","").strip() or "(none)")
    tpath.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return tpath, jpath

def main() -> int:
    here = Path(__file__).resolve()
    root = find_root(here.parent.parent if here.parent.name == "scripts" else here.parent)
    outputs = root / "outputs"
    qa_dir = outputs / "qa"
    payload = {"ok": False, "root": str(root), "outputs": str(outputs), "generator": None, "checks": None}
    cmd = pick_generator_cmd(root)
    if cmd:
        try:
            payload["generator"] = run(cmd, cwd=root)
        except Exception as e:
            payload["generator"] = {"cmd": cmd, "returncode": 999, "stdout": "", "stderr": repr(e)}
    checks = check_outputs(outputs)
    payload["checks"] = checks
    payload["ok"] = checks["ok"] and (payload["generator"] is None or payload["generator"]["returncode"] == 0)
    tpath, jpath = write_reports(qa_dir, payload)
    print(f"QA_REPORT:{tpath}")
    print(f"QA_JSON:{jpath}")
    print("PASS" if payload["ok"] else "FAIL")
    return 0 if payload["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())

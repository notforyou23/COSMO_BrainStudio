#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

def _canonical_root(start: Path | None = None) -> Path:
    p = (start or Path(__file__)).resolve()
    for d in [p, *p.parents]:
        cc = d / "runtime" / "outputs" / "code-creation"
        if cc.is_dir():
            return d
    return p.parents[4] if len(p.parents) >= 5 else p.parent

def _find_newest_init_outputs(repo_root: Path) -> Path:
    base = repo_root / "runtime" / "outputs" / "code-creation"
    cands = sorted(base.rglob("src/init_outputs.py"))
    if not cands:
        raise FileNotFoundError(f"No init_outputs.py found under: {base}")
    return max(cands, key=lambda p: p.stat().st_mtime)

def _ts_utc() -> str:
    # deterministic, filesystem-friendly UTC timestamp with milliseconds
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H-%M-%S-") + f"{int(dt.microsecond/1000):03d}Z"

def _run_and_capture(py_file: Path, cwd: Path) -> tuple[int, str, str]:
    p = subprocess.run(
        [sys.executable, str(py_file)],
        cwd=str(cwd),
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    return p.returncode, p.stdout, p.stderr

def main() -> int:
    root = _canonical_root()
    print(f"CANONICAL_PROJECT_ROOT:{root}")
    init_py = _find_newest_init_outputs(root)
    print(f"INIT_OUTPUTS_PY:{init_py}")

    qa_dir = root / "outputs" / "qa"
    qa_dir.mkdir(parents=True, exist_ok=True)

    rc, out, err = _run_and_capture(init_py, cwd=root)

    log_path = qa_dir / f"init_outputs_run_{_ts_utc()}.log"
    header = [
        f"timestamp_utc={datetime.now(timezone.utc).isoformat()}",
        f"canonical_project_root={root}",
        f"init_outputs_py={init_py}",
        f"returncode={rc}",
        "",
        "===== STDOUT =====",
        out.rstrip("\n"),
        "",
        "===== STDERR =====",
        err.rstrip("\n"),
        "",
    ]
    log_path.write_text("\n".join(header) + "\n", encoding="utf-8")

    print(f"QA_LOG:{log_path}")
    return rc

if __name__ == "__main__":
    raise SystemExit(main())

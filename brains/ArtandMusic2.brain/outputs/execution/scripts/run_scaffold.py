#!/usr/bin/env python3
from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _make_has_target(makefile: Path, target: str) -> bool:
    txt = _read_text(makefile)
    if not txt:
        return False
    for line in txt.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("."):
            continue
        if s.startswith(target + ":"):
            return True
    return False


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(cmd, cwd=str(cwd))
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    env_cmd = os.environ.get("SCAFFOLD_COMMAND", "").strip()
    if env_cmd:
        cmd = shlex.split(env_cmd)
        _run(cmd, root)
        return 0

    makefile = root / "Makefile"
    if makefile.exists():
        for tgt in ("scaffold", "generate", "gen", "build_scaffold"):
            if _make_has_target(makefile, tgt):
                _run(["make", tgt], root)
                return 0

    scripts_dir = root / "scripts"
    candidates: list[Path] = []
    for rel in (
        "scripts/generate_scaffold.py",
        "scripts/scaffold.py",
        "scripts/generate.py",
        "scripts/generator.py",
        "scripts/run_generator.py",
        "generate_scaffold.py",
        "scaffold.py",
        "generate.py",
        "generator.py",
    ):
        p = root / rel
        if p.exists() and p.is_file():
            candidates.append(p)

    self_path = Path(__file__).resolve()
    candidates = [p for p in candidates if p.resolve() != self_path]

    if candidates:
        chosen = sorted({p.resolve() for p in candidates})[0]
        _run([sys.executable, str(chosen)], root)
        return 0

    # No scaffold generator found; treat as a no-op success for CI compatibility.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

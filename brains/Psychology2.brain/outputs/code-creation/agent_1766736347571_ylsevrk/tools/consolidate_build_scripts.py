#!/usr/bin/env python3
"""Consolidate duplicate build/verify scripts into a canonical pair.

Scans the repo for build_runner.py and verify_artifacts.py (often duplicated in agent outputs),
selects the best candidates via simple heuristics, normalizes them so outputs land in runtime/_build/,
and installs them to scripts/build_runner.py and scripts/verify_artifacts.py.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple, List


CANONICAL_DIR = Path("scripts")
CANONICAL_RUNNER = CANONICAL_DIR / "build_runner.py"
CANONICAL_VERIFIER = CANONICAL_DIR / "verify_artifacts.py"
CANONICAL_COMMON = CANONICAL_DIR / "_build_common.py"
BUILD_DIR_REL = Path("runtime") / "_build"


@dataclass
class Candidate:
    path: Path
    score: int
    mtime: float


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _score_script(p: Path, text: str) -> int:
    t = text
    s = 0
    s += min(len(t) // 40, 500)
    for kw, pts in [
        ("argparse", 120),
        ("subprocess", 90),
        ("Path(", 60),
        ("runtime/_build", 220),
        ("runtime\\_build", 220),
        ("BUILD_DIR", 60),
        ("verify", 30),
        ("artifacts", 30),
        ("__name__ == "__main__"", 60),
    ]:
        if kw in t:
            s += pts
    s -= 200 if re.search(r"\bTODO\b|placeholder|pass\s*(#.*)?\n", t, re.IGNORECASE) else 0
    s -= 120 if "raise NotImplementedError" in t else 0
    return s


def _iter_candidates(search_root: Path, filename: str) -> Iterable[Candidate]:
    ignore_parts = {".git", "__pycache__", ".venv", "venv", "site-packages", "node_modules"}
    for p in search_root.rglob(filename):
        if any(part in ignore_parts for part in p.parts):
            continue
        if p.as_posix().endswith(str(CANONICAL_RUNNER)) or p.as_posix().endswith(str(CANONICAL_VERIFIER)):
            continue
        txt = _read_text(p)
        if not txt.strip():
            continue
        try:
            st = p.stat()
            mtime = float(st.st_mtime)
        except Exception:
            mtime = 0.0
        yield Candidate(path=p, score=_score_script(p, txt), mtime=mtime)


def _pick_best(cands: Iterable[Candidate]) -> Optional[Candidate]:
    best = None
    for c in cands:
        if best is None:
            best = c
            continue
        if (c.score, c.mtime) > (best.score, best.mtime):
            best = c
    return best


def _normalize_text(text: str, kind: str) -> str:
    # Ensure runtime/_build is used (best-effort).
    t = text.replace("runtime\\build", "runtime/_build").replace("runtime/build", "runtime/_build")
    t = t.replace("runtime\\_build", "runtime/_build")
    # Nudge common patterns to target runtime/_build.
    t = re.sub(r"(?m)^(\s*)(BUILD_DIR|build_dir|out_dir|output_dir)\s*=\s*['\"]([^'\"]+)['\"]\s*$",
               r"\1\2 = 'runtime/_build'", t)
    return t


def _shim_header() -> str:
    return (
        "from __future__ import annotations\n"
        "import os\n"
        "from pathlib import Path\n"
        "_REPO_ROOT = Path(__file__).resolve().parents[1]\n"
        "os.chdir(_REPO_ROOT)\n"
        "_BUILD_DIR = _REPO_ROOT / 'runtime' / '_build'\n"
        "_BUILD_DIR.mkdir(parents=True, exist_ok=True)\n"
        "os.environ.setdefault('COSMO_BUILD_DIR', str(_BUILD_DIR))\n"
    )


def _write_canonical(repo_root: Path, runner_src: Path, verifier_src: Path, dry_run: bool = False) -> None:
    scripts_dir = repo_root / CANONICAL_DIR
    if not dry_run:
        scripts_dir.mkdir(parents=True, exist_ok=True)

    common = (
        "from __future__ import annotations\n"
        "import os, subprocess\n"
        "from pathlib import Path\n\n"
        "REPO_ROOT = Path(__file__).resolve().parents[1]\n"
        "BUILD_DIR = REPO_ROOT / 'runtime' / '_build'\n"
        "BUILD_DIR.mkdir(parents=True, exist_ok=True)\n\n"
        "def chdir_repo() -> None:\n"
        "    os.chdir(REPO_ROOT)\n\n"
        "def run(cmd, *, cwd=None, env=None, capture=True, check=False):\n"
        "    chdir_repo()\n"
        "    e = os.environ.copy()\n"
        "    e.setdefault('COSMO_BUILD_DIR', str(BUILD_DIR))\n"
        "    if env: e.update(env)\n"
        "    return subprocess.run(cmd, cwd=cwd or REPO_ROOT, env=e, text=True,\n"
        "        capture_output=capture, check=check)\n"
    )

    runner_txt = _normalize_text(_read_text(runner_src), "runner")
    verifier_txt = _normalize_text(_read_text(verifier_src), "verifier")

    runner_out = _shim_header() + "\n" + runner_txt.lstrip("\n")
    verifier_out = _shim_header() + "\n" + verifier_txt.lstrip("\n")

    if not dry_run:
        (repo_root / CANONICAL_COMMON).write_text(common, encoding="utf-8")
        (repo_root / CANONICAL_RUNNER).write_text(runner_out, encoding="utf-8")
        (repo_root / CANONICAL_VERIFIER).write_text(verifier_out, encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Consolidate build_runner.py and verify_artifacts.py into scripts/.")
    ap.add_argument("--repo-root", default=None, help="Repo root (default: parent of tools/).")
    ap.add_argument("--search-root", default=None, help="Where to scan (default: repo root).")
    ap.add_argument("--dry-run", action="store_true", help="Do not write files.")
    ap.add_argument("--print", dest="do_print", action="store_true", help="Print selected candidates.")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[1]
    search_root = Path(args.search_root).resolve() if args.search_root else repo_root

    best_runner = _pick_best(_iter_candidates(search_root, "build_runner.py"))
    best_verifier = _pick_best(_iter_candidates(search_root, "verify_artifacts.py"))
    if not best_runner or not best_verifier:
        print("ERROR: missing candidates:", "build_runner.py" if not best_runner else "", "verify_artifacts.py" if not best_verifier else "")
        return 2

    if args.do_print:
        print(f"SELECTED build_runner.py: {best_runner.path} (score={best_runner.score})")
        print(f"SELECTED verify_artifacts.py: {best_verifier.path} (score={best_verifier.score})")

    _write_canonical(repo_root, best_runner.path, best_verifier.path, dry_run=args.dry_run)
    if not args.dry_run:
        print(f"INSTALLED: {CANONICAL_RUNNER} {CANONICAL_VERIFIER} (build outputs -> {BUILD_DIR_REL})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path


def eprint(*a: object) -> None:
    print(*a, file=sys.stderr)


def run_cmd(cmd: str, cwd: Path) -> int:
    eprint(f"[ci] RUN: {cmd}")
    p = subprocess.run(cmd, shell=True, cwd=str(cwd), env=os.environ.copy())
    return int(p.returncode)


def find_cmd(repo: Path, candidates: list[str]) -> str | None:
    for cmd in candidates:
        parts = shlex.split(cmd)
        if not parts:
            continue
        if parts[0] == "python" and len(parts) >= 2:
            target = repo / parts[1]
            if target.exists():
                return cmd
        if parts[0].startswith("./"):
            target = repo / parts[0][2:]
            if target.exists():
                return cmd
        # module form, accept as-is
        if parts[0] == "python" and "-m" in parts:
            return cmd
    return None


def load_expectations(repo: Path, path: Path | None) -> dict:
    if path is None:
        path = repo / "scripts" / "ci_expectations.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise SystemExit(f"[ci] expectations must be a JSON object: {path}")
        data["_path"] = str(path)
        return data
    return {
        "_path": None,
        "required": ["runtime/_build", "runtime/_build/reports", "runtime/_build/figures"],
    }


def norm_required(req) -> list[str]:
    if req is None:
        return []
    if isinstance(req, str):
        return [req]
    if isinstance(req, list) and all(isinstance(x, str) for x in req):
        return req
    raise SystemExit("[ci] expectations.required must be a string or list of strings")


def check_required(repo: Path, required: list[str]) -> tuple[list[str], list[str]]:
    ok, missing = [], []
    for rel in required:
        p = repo / rel
        (ok if p.exists() else missing).append(rel)
    return ok, missing


def list_tree(root: Path, max_items: int = 80) -> list[str]:
    if not root.exists():
        return [f"{root} (missing)"]
    items = []
    for p in sorted(root.rglob("*")):
        if len(items) >= max_items:
            items.append("... (truncated)")
            break
        try:
            rel = p.relative_to(root)
        except Exception:
            rel = p
        suffix = "/" if p.is_dir() else ""
        items.append(str(rel) + suffix)
    return items or ["(empty)"]


def main() -> int:
    ap = argparse.ArgumentParser(description="CI entrypoint: run validator+demos and assert expected outputs exist.")
    ap.add_argument("--repo-root", default=".", help="Repo root (default: current working directory).")
    ap.add_argument("--validator-cmd", default=None, help="Override validator command.")
    ap.add_argument("--demo-cmd", default=None, help="Override demo runner command.")
    ap.add_argument("--expectations", default=None, help="Path to expectations JSON (default: scripts/ci_expectations.json).")
    ap.add_argument("--skip-validator", action="store_true")
    ap.add_argument("--skip-demos", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo_root).resolve()
    exp_path = Path(args.expectations).resolve() if args.expectations else None
    exp = load_expectations(repo, exp_path)

    validator = args.validator_cmd
    demo = args.demo_cmd
    if validator is None and not args.skip_validator:
        validator = find_cmd(repo, [
            "python scripts/validate.py",
            "python scripts/validator.py",
            "python -m scripts.validate",
            "python -m scripts.validator",
            "python -m validator",
            "./scripts/validate",
        ])
    if demo is None and not args.skip_demos:
        demo = find_cmd(repo, [
            "python scripts/run_demos.py",
            "python scripts/demo_runner.py",
            "python -m scripts.run_demos",
            "python -m scripts.demo_runner",
            "python -m demo_runner",
            "./scripts/run_demos",
        ])

    if not args.skip_validator:
        if not validator:
            eprint("[ci] ERROR: could not infer validator command. Pass --validator-cmd or --skip-validator.")
            return 2
        rc = run_cmd(validator, repo)
        if rc != 0:
            eprint(f"[ci] ERROR: validator failed with exit code {rc}")
            return rc
    if not args.skip_demos:
        if not demo:
            eprint("[ci] ERROR: could not infer demo runner command. Pass --demo-cmd or --skip-demos.")
            return 2
        rc = run_cmd(demo, repo)
        if rc != 0:
            eprint(f"[ci] ERROR: demo runner failed with exit code {rc}")
            return rc

    required = norm_required(exp.get("required"))
    ok, missing = check_required(repo, required)
    if missing:
        eprint("[ci] ERROR: missing required CI outputs:")
        for rel in missing:
            eprint(f"  - {rel}")
        eprint("[ci] Present required outputs:")
        for rel in ok:
            eprint(f"  + {rel}")
        build_root = repo / "runtime" / "_build"
        eprint(f"[ci] runtime/_build tree snapshot ({build_root}):")
        for line in list_tree(build_root):
            eprint(f"  {line}")
        src = exp.get("_path")
        eprint(f"[ci] Expectations source: {src or '(defaults in scripts/ci_run.py)'}")
        return 3

    eprint(f"[ci] OK: all required outputs exist ({len(required)} checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

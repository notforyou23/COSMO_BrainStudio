#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_CREATE_FAILED = 10
EXIT_CHECK_FAILED = 11

DEFAULT_REQUIRED_DIRS = ("artifacts", "logs", "reports", "data")
README_NAME = "README.md"

def _nonempty_file(p: Path) -> bool:
    try:
        return p.is_file() and p.stat().st_size > 0
    except OSError:
        return False

def _next_changelog_version(outputs_dir: Path) -> int:
    mx = 0
    for p in outputs_dir.glob("CHANGELOG_v*.md"):
        s = p.stem
        if s.startswith("CHANGELOG_v"):
            n = s.split("CHANGELOG_v", 1)[1]
            if n.isdigit():
                mx = max(mx, int(n))
    return mx + 1 if mx > 0 else 1

def _changelog_path(outputs_dir: Path, version: int) -> Path:
    return outputs_dir / f"CHANGELOG_v{version}.md"

def local_create_and_check(root: Path, outputs_name: str = "outputs", version: int | None = None):
    outputs_dir = root / outputs_name
    outputs_dir.mkdir(parents=True, exist_ok=True)
    for d in DEFAULT_REQUIRED_DIRS:
        (outputs_dir / d).mkdir(parents=True, exist_ok=True)

    readme = outputs_dir / README_NAME
    if not readme.exists():
        readme.write_text(
            "# outputs\n\n"
            "This directory contains run artifacts produced by the project.\n\n"
            "Required structure:\n"
            "- artifacts/\n- logs/\n- reports/\n- data/\n\n"
            "Gate: README and a versioned CHANGELOG must exist and be non-empty.\n",
            encoding="utf-8",
        )

    if version is None:
        version = _next_changelog_version(outputs_dir)
    changelog = _changelog_path(outputs_dir, version)
    if not changelog.exists():
        changelog.write_text(
            f"# Changelog (v{version})\n\n"
            "- Initialized artifact gate outputs structure.\n",
            encoding="utf-8",
        )

    ok, issues = local_check(root, outputs_name=outputs_name)
    return {"outputs_dir": str(outputs_dir), "created_changelog": str(changelog), "ok": ok, "issues": issues}

def local_check(root: Path, outputs_name: str = "outputs"):
    outputs_dir = root / outputs_name
    issues = []
    if not outputs_dir.is_dir():
        issues.append(f"Missing outputs directory: {outputs_dir}")
        return False, issues

    for d in DEFAULT_REQUIRED_DIRS:
        p = outputs_dir / d
        if not p.is_dir():
            issues.append(f"Missing required directory: {p}")

    readme = outputs_dir / README_NAME
    if not _nonempty_file(readme):
        issues.append(f"Missing or empty required file: {readme}")

    changelogs = sorted(outputs_dir.glob("CHANGELOG_v*.md"))
    if not changelogs:
        issues.append(f"Missing required changelog: {outputs_dir}/CHANGELOG_v*.md")
    else:
        if not any(_nonempty_file(p) for p in changelogs):
            issues.append("All changelogs are empty.")

    return (len(issues) == 0), issues

def resolve_impl():
    try:
        from src.artifact_gate import create_outputs_and_check  # type: ignore
        return "module", create_outputs_and_check
    except Exception:
        return "local", None

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Create /outputs artifacts and verify existence/non-empty gate.")
    ap.add_argument("--root", default=".", help="Project root containing outputs/ (default: .)")
    ap.add_argument("--outputs-dir", default="outputs", help="Outputs directory name (default: outputs)")
    ap.add_argument("--version", type=int, default=None, help="Changelog version to create (default: auto-increment)")
    ap.add_argument("--check-only", action="store_true", help="Only run checks; do not create missing artifacts")
    ap.add_argument("--create-only", action="store_true", help="Only create artifacts; do not run checks")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON summary")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    impl_kind, create_fn = resolve_impl()

    if args.check_only and args.create_only:
        print("ERROR: --check-only and --create-only are mutually exclusive", file=sys.stderr)
        return EXIT_USAGE

    if impl_kind == "module" and create_fn is not None:
        try:
            res = create_fn(root=root, outputs_dir=args.outputs_dir, version=args.version,
                            check_only=args.check_only, create_only=args.create_only)
        except TypeError:
            res = create_fn(root=root, outputs_dir=args.outputs_dir, version=args.version)
        except Exception as e:
            if args.json:
                print(json.dumps({"ok": False, "error": str(e)}))
            else:
                print(f"ERROR: artifact gate failed: {e}", file=sys.stderr)
            return EXIT_CREATE_FAILED
        ok = bool(res.get("ok", False)) if isinstance(res, dict) else bool(res)
        issues = res.get("issues", []) if isinstance(res, dict) else []
    else:
        if args.check_only:
            ok, issues = local_check(root, outputs_name=args.outputs_dir)
            res = {"ok": ok, "issues": issues, "impl": "local"}
        else:
            res = local_create_and_check(root, outputs_name=args.outputs_dir, version=args.version)
            ok, issues = res["ok"], res["issues"]
            if args.create_only:
                ok, issues = True, []
                res["ok"], res["issues"] = ok, issues

    if args.json:
        out = dict(res) if isinstance(res, dict) else {"ok": ok, "issues": issues}
        out.setdefault("root", str(root))
        out.setdefault("outputs_dir", str((root / args.outputs_dir)))
        out.setdefault("impl", impl_kind)
        print(json.dumps(out, indent=2, sort_keys=True))
    else:
        if ok:
            print("OK: artifact gate passed")
        else:
            print("FAIL: artifact gate failed", file=sys.stderr)
            for it in issues:
                print(f"- {it}", file=sys.stderr)

    if ok:
        return EXIT_OK
    return EXIT_CHECK_FAILED if (args.check_only or impl_kind != "module") else EXIT_CREATE_FAILED

if __name__ == "__main__":
    raise SystemExit(main())

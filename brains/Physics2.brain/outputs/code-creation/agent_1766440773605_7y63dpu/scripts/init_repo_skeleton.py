#!/usr/bin/env python3
"""Initialize a small, safe Python CLI repository skeleton.

This script creates a minimal src/ layout with a package, tests/, and common
project files. It avoids overwriting existing files unless --force is used.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, Mapping


DEFAULT_PKG = "dgpipe"
DEFAULT_VERSION = "0.1.0"


def _ensure_dir(path: Path, *, dry_run: bool) -> None:
    if dry_run:
        return
    path.mkdir(parents=True, exist_ok=True)


def _write_file(path: Path, content: str, *, force: bool, dry_run: bool) -> bool:
    """Write content to path. Returns True if created/updated."""
    if path.exists() and not force:
        return False
    if dry_run:
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _render_files(pkg: str, version: str) -> Mapping[str, str]:
    pkg_dir = f"src/{pkg}"
    return {
        "README.md": f"# {pkg}\n\nGenerated skeleton.\n",
        ".gitignore": "__pycache__/\n*.pyc\n.venv/\ndist/\nbuild/\n.pytest_cache/\n",
        "pyproject.toml": (
            "[build-system]\n"
            "requires = [\"setuptools>=68\"]\n"
            "build-backend = \"setuptools.build_meta\"\n\n"
            "[project]\n"
            f"name = \"{pkg}\"\n"
            f"version = \"{version}\"\n"
            "requires-python = \">=3.9\"\n"
            "dependencies = []\n\n"
            "[project.scripts]\n"
            f"{pkg} = \"{pkg}.cli:main\"\n"
        ),
        f"{pkg_dir}/__init__.py": (
            '"""Public package interface."""\n\n'
            f"__all__ = [\"__version__\"]\n"
            f"__version__ = \"{version}\"\n"
        ),
        f"{pkg_dir}/cli.py": (
            '"""Small example CLI entrypoint."""\n\n'
            "import argparse\n\n\n"
            "def build_parser() -> argparse.ArgumentParser:\n"
            f"    p = argparse.ArgumentParser(prog=\"{pkg}\")\n"
            "    p.add_argument(\"--version\", action=\"store_true\", help=\"print version\")\n"
            "    return p\n\n\n"
            "def main(argv: list[str] | None = None) -> int:\n"
            "    args = build_parser().parse_args(argv)\n"
            "    if args.version:\n"
            f"        print(\"{version}\")\n"
            "        return 0\n"
            "    print(\"OK\")\n"
            "    return 0\n"
        ),
        "tests/test_smoke.py": (
            "def test_imports():\n"
            f"    import {pkg}  # noqa: F401\n"
            f"    import {pkg}.cli  # noqa: F401\n"
        ),
        "scripts/__init__.py": "\n",
    }


def init_skeleton(root: Path, *, pkg: str, version: str, force: bool, dry_run: bool) -> list[Path]:
    created: list[Path] = []
    for d in [root / "src", root / "tests", root / "scripts", root / "src" / pkg]:
        _ensure_dir(d, dry_run=dry_run)
    files = _render_files(pkg, version)
    for rel, content in files.items():
        p = root / rel
        if _write_file(p, content, force=force, dry_run=dry_run):
            created.append(p)
    return created


def _parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Initialize a minimal Python CLI repository skeleton (src/ layout).",
    )
    p.add_argument("root", nargs="?", default=".", help="directory to initialize (default: current)")
    p.add_argument("--package-name", default=DEFAULT_PKG, help=f"package name (default: {DEFAULT_PKG})")
    p.add_argument("--version", default=DEFAULT_VERSION, help=f"package version (default: {DEFAULT_VERSION})")
    p.add_argument("--force", action="store_true", help="overwrite existing files")
    p.add_argument("--dry-run", action="store_true", help="do not write anything; only report")
    return p.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv)
    root = Path(args.root).resolve()
    created = init_skeleton(
        root, pkg=args.package_name, version=args.version, force=args.force, dry_run=args.dry_run
    )
    if args.dry_run:
        for p in created:
            print(f"WOULD_WRITE:{p.relative_to(root)}")
    else:
        for p in created:
            print(f"WROTE:{p.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

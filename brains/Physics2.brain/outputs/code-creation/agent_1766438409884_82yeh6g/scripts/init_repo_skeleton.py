#!/usr/bin/env python3
"""Create a versioned repository skeleton under the outputs directory.

This script is idempotent by default: it creates missing folders/files and
does not overwrite existing files unless --overwrite is provided.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
def _write_if_missing(path: Path, content: str, overwrite: bool) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _repo_contents(project_name: str) -> dict[str, str]:
    year = "2025"
    readme = f"""# {project_name}

This repository skeleton is generated into **outputs/** for auditable, versioned deliverables.
It includes standard documentation and placeholder modules so work products are always captured.

## Structure

- `docs/` documentation hub and pages
- `src/` source code package placeholder
- `scripts/` helper scripts placeholder
- `tests/` test placeholder
- `outputs/` location for generated artifacts (kept in-repo for audits)

## Generate

From the repository root:

```bash
python scripts/init_repo_skeleton.py
```

Re-run safely at any time; use `--overwrite` to refresh file contents.
"""
    license_txt = f"""MIT License

Copyright (c) {year}

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    contributing = """# Contributing

## Workflow

- Create a feature branch from `main`.
- Keep changes small and focused; update docs alongside code.
- Prefer deterministic scripts and idempotent generators.

## Formatting

- Python: PEP 8, type hints where useful.
- Markdown: wrap at ~100 chars when practical; use clear headings.

## Adding deliverables

- Put generated artifacts under `outputs/` and document them in `docs/`.
- Do not overwrite existing audited artifacts unless there is a clear version bump.
"""
    docs_readme = """# Documentation

This is the documentation hub.

## Where things live

- Audit-ready deliverables: `../outputs/`
- Design notes and decisions: add markdown pages in this folder

## Suggested pages

- `architecture.md`
- `roadmap.md`
- `deliverables.md`
"""
    pkg_init = """\"\"\"Package placeholder for source code.\"\"\"\n"
    scripts_readme = """# Scripts

Place helper scripts here (build, export, validation, etc.).
"""
    tests_readme = """# Tests

Place unit/integration tests here.
"""
    outputs_readme = """# Outputs

Generated artifacts and audit deliverables live here. Keep this folder versioned.
"""
    gitignore = """__pycache__/
*.pyc
.venv/
.env
.DS_Store
"""
    return {
        "README.md": readme,
        "LICENSE": license_txt,
        "CONTRIBUTING.md": contributing,
        "docs/README.md": docs_readme,
        "docs/architecture.md": "# Architecture\n\nHigh-level system architecture notes.\n",
        "docs/roadmap.md": "# Roadmap\n\nPlanned milestones and documentation outline.\n",
        "docs/deliverables.md": "# Deliverables\n\nIndex of deliverables and where they are stored under `outputs/`.\n",
        "src/__init__.py": pkg_init,
        "scripts/README.md": scripts_readme,
        "tests/README.md": tests_readme,
        "outputs/README.md": outputs_readme,
        ".gitignore": gitignore,
        "pyproject.toml": """[project]
name = \"repo-skeleton\"
version = \"0.1.0\"
requires-python = \">=3.10\"
""",
    }
def init_repo_skeleton(root: Path, project_name: str, overwrite: bool = False) -> dict[str, int]:
    files = _repo_contents(project_name)
    created = 0
    updated = 0
    for rel, content in files.items():
        p = root / rel
        existed = p.exists()
        changed = _write_if_missing(p, content, overwrite=overwrite)
        if changed and existed:
            updated += 1
        elif changed:
            created += 1
    # Ensure directories exist even if no files are written into them in the future.
    for d in ("docs", "src", "scripts", "tests", "outputs"):
        (root / d).mkdir(parents=True, exist_ok=True)
    return {"created": created, "updated": updated, "root": 1}


def _parse_args(argv: list[str]) -> argparse.Namespace:
    default_root = Path("/mnt/data/outputs/repo_skeleton")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=default_root, help=f"Target root (default: {default_root})")
    p.add_argument("--name", default="Audit Repository Skeleton", help="Project name used in README")
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    ns = _parse_args(sys.argv[1:] if argv is None else argv)
    root = ns.root
    root.mkdir(parents=True, exist_ok=True)
    stats = init_repo_skeleton(root=root, project_name=ns.name, overwrite=ns.overwrite)
    print(f"ROOT:{root}")
    print(f"CREATED:{stats['created']}")
    print(f"UPDATED:{stats['updated']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

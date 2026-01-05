from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Union


OUTPUTS_README = """# /outputs artifact contract

This folder is the *stable artifact surface* produced by this project.

## Rules
- Write only within /outputs (or a caller-provided outputs directory).
- Be idempotent: re-running should not corrupt or delete existing artifacts.
- Never overwrite user-authored content; create missing files/directories only.
- Prefer additive updates (append entries, create new versioned files).
- Keep filenames deterministic and descriptive; avoid spaces when possible.

## Structure
- /outputs/README.md: this contract and directory overview
- /outputs/CHANGELOG.md: cycle-based changelog of structural/artifact updates
- /outputs/meta_analysis/: cross-run synthesis, QA, evaluation summaries
- /outputs/taxonomy/: schemas, label sets, mapping tables, taxonomy notes
- /outputs/tooling/: helper outputs (diagnostics, reports, helper exports)

## Safe writing
- Create missing directories and README files as needed.
- When an output is created or structurally modified, append an entry to
  /outputs/CHANGELOG.md describing what changed and why.
"""


CHANGELOG_HEADER = """# /outputs CHANGELOG

All notable changes to the /outputs artifact surface are documented here.
Entries are appended per cycle/run when outputs are created or modified.

"""


META_ANALYSIS_README = """# /outputs/meta_analysis

Contents: cross-run syntheses, evaluation summaries, QA notes, and meta-level analyses.
Expectations:
- Include minimal provenance (timestamp, inputs referenced, tool/version if relevant).
- Prefer Markdown for narrative and CSV/JSON for tabular or structured artifacts.
"""


TAXONOMY_README = """# /outputs/taxonomy

Contents: taxonomies, schemas, label sets, and mapping tables used by the project.
Expectations:
- Document schema conventions and any breaking changes.
- When updating a taxonomy, record the change in /outputs/CHANGELOG.md.
"""


TOOLING_README = """# /outputs/tooling

Contents: helper artifacts produced by tooling (diagnostics, exported configs, reports).
Expectations:
- Keep outputs reproducible and clearly named.
- Avoid placing sensitive data here unless explicitly permitted.
"""


@dataclass(frozen=True)
class ScaffoldResult:
    outputs_dir: Path
    created: Tuple[Path, ...]
    touched: Tuple[Path, ...]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _cycle_id(explicit: Optional[str] = None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    return _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return True


def _mkdir_if_missing(path: Path) -> bool:
    if path.exists():
        return False
    path.mkdir(parents=True, exist_ok=True)
    return True


def _append_changelog(changelog: Path, cycle: str, changes: Iterable[str]) -> bool:
    changes = [c.strip() for c in changes if c and c.strip()]
    if not changes:
        return False
    if not changelog.exists():
        _write_if_missing(changelog, CHANGELOG_HEADER)
    entry = ["## Cycle " + cycle, ""]
    entry += [f"- {c}" for c in changes]
    entry.append("")
    with changelog.open("a", encoding="utf-8") as f:
        f.write("\n".join(entry))
    return True


def scaffold_outputs(base_dir: Union[str, Path], *, outputs_dirname: str = "outputs", cycle: Optional[str] = None) -> ScaffoldResult:
    """Create /outputs structure and readmes idempotently; update CHANGELOG when changes occur."""
    base = Path(base_dir).expanduser().resolve()
    out = base / outputs_dirname
    created: List[Path] = []
    touched: List[Path] = []
    changes: List[str] = []

    if _mkdir_if_missing(out):
        created.append(out)
        changes.append("Created outputs root directory.")

    readme = out / "README.md"
    if _write_if_missing(readme, OUTPUTS_README):
        created.append(readme)
        changes.append("Created outputs/README.md artifact contract.")

    changelog = out / "CHANGELOG.md"
    if _write_if_missing(changelog, CHANGELOG_HEADER):
        created.append(changelog)
        changes.append("Created outputs/CHANGELOG.md.")

    for sub, text in [
        ("meta_analysis", META_ANALYSIS_README),
        ("taxonomy", TAXONOMY_README),
        ("tooling", TOOLING_README),
    ]:
        d = out / sub
        if _mkdir_if_missing(d):
            created.append(d)
            changes.append(f"Created outputs/{sub}/ directory.")
        r = d / "README.md"
        if _write_if_missing(r, text):
            created.append(r)
            changes.append(f"Created outputs/{sub}/README.md.")

    if _append_changelog(changelog, _cycle_id(cycle), changes):
        touched.append(changelog)

    return ScaffoldResult(outputs_dir=out, created=tuple(created), touched=tuple(touched))

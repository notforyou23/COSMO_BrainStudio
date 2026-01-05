from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


OUTPUTS_DIRNAME = "outputs"
REQUIRED_DIRS = ("artifacts", "docs", "logs", "reports")
REQUIRED_FILES = ("README.md", "CHANGELOG.md")


@dataclass(frozen=True)
class GateResult:
    ok: bool
    missing: Tuple[str, ...] = ()
    empty: Tuple[str, ...] = ()
    details: str = ""


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_latest_version(changelog_text: str) -> Optional[str]:
    for line in changelog_text.splitlines():
        s = line.strip()
        if s.startswith("## [") and "]" in s:
            return s.split("[", 1)[1].split("]", 1)[0].strip()
    return None


def _bump_patch(version: str) -> str:
    parts = version.strip().split(".")
    nums = [int(p) for p in parts[:3]] + [0] * (3 - len(parts[:3]))
    nums[2] += 1
    return ".".join(str(n) for n in nums[:3])


def ensure_outputs_structure(base_dir: Path, version: Optional[str] = None) -> Dict[str, Path]:
    base_dir = Path(base_dir)
    outputs = base_dir / OUTPUTS_DIRNAME
    outputs.mkdir(parents=True, exist_ok=True)
    for d in REQUIRED_DIRS:
        (outputs / d).mkdir(parents=True, exist_ok=True)

    readme = outputs / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Outputs

"
            "This directory contains cycle artifacts produced by the project.

"
            "## Required structure
"
            + "".join(f"- `{d}/`
" for d in REQUIRED_DIRS)
            + "
## Completion gate
"
            "- `README.md` and `CHANGELOG.md` must exist and be non-empty.
"
            "- Subfolders listed above must exist.
",
            encoding="utf-8",
        )

    changelog = outputs / "CHANGELOG.md"
    if changelog.exists():
        text = changelog.read_text(encoding="utf-8")
        latest = _parse_latest_version(text) or "0.1.0"
        next_version = version or _bump_patch(latest)
        if f"## [{next_version}]" not in text:
            entry = (
                f"## [{next_version}] - {_utc_date()}
"
                "- Initialize/verify outputs artifact gate.

"
            )
            changelog.write_text(text.rstrip() + "

" + entry, encoding="utf-8")
    else:
        v = version or "0.1.0"
        changelog.write_text(
            "# Changelog

"
            "All notable changes to the outputs artifacts are documented in this file.

"
            f"## [{v}] - {_utc_date()}
"
            "- Initialize outputs structure and artifact success gate.
",
            encoding="utf-8",
        )

    return {
        "outputs": outputs,
        "readme": readme,
        "changelog": changelog,
        **{d: outputs / d for d in REQUIRED_DIRS},
    }


def check_required_artifacts(base_dir: Path) -> GateResult:
    base_dir = Path(base_dir)
    outputs = base_dir / OUTPUTS_DIRNAME

    missing: List[str] = []
    empty: List[str] = []

    if not outputs.is_dir():
        missing.append(str(outputs))
        return GateResult(False, tuple(missing), tuple(empty), "outputs directory missing")

    for d in REQUIRED_DIRS:
        p = outputs / d
        if not p.is_dir():
            missing.append(str(p))

    for f in REQUIRED_FILES:
        p = outputs / f
        if not p.is_file():
            missing.append(str(p))
        else:
            try:
                if p.stat().st_size <= 0:
                    empty.append(str(p))
            except OSError:
                empty.append(str(p))

    ok = not missing and not empty
    details = "ok" if ok else "missing and/or empty required artifacts"
    return GateResult(ok, tuple(missing), tuple(empty), details)


def run_gate(base_dir: Path, version: Optional[str] = None, create: bool = True) -> GateResult:
    base_dir = Path(base_dir)
    if create:
        ensure_outputs_structure(base_dir, version=version)
    return check_required_artifacts(base_dir)

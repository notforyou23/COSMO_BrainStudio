from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable, Optional

CASE_STUDIES_DIRNAME = "case-studies"
CASE_METADATA_FILENAME = "metadata.json"


def package_root() -> Path:
    return Path(__file__).resolve().parent


def project_root() -> Path:
    # src/case_studies -> src -> project
    return package_root().parent.parent


def find_case_studies_root(start: Optional[Path] = None) -> Path:
    """Find the case-studies root by searching upwards from *start*.

    Resolution order:
      1) any ancestor containing CASE_STUDIES_DIRNAME/
      2) project_root()/CASE_STUDIES_DIRNAME
    """
    start_path = (start or Path.cwd()).resolve()
    for p in [start_path, *start_path.parents]:
        candidate = p / CASE_STUDIES_DIRNAME
        if candidate.is_dir():
            return candidate
    fallback = project_root() / CASE_STUDIES_DIRNAME
    return fallback


_slug_re = re.compile(r"[^a-z0-9]+")


def canonical_slug(value: str) -> str:
    """Convert an arbitrary string into a filesystem-friendly slug."""
    v = (value or "").strip().lower()
    v = _slug_re.sub("-", v)
    v = re.sub(r"-{2,}", "-", v).strip("-")
    if not v:
        raise ValueError("slug is empty after canonicalization")
    if v in {".", ".."}:
        raise ValueError("invalid slug")
    return v


def case_dir(case_studies_root: Path, slug: str) -> Path:
    return case_studies_root / canonical_slug(slug)


def case_metadata_path(case_studies_root: Path, slug: str) -> Path:
    return case_dir(case_studies_root, slug) / CASE_METADATA_FILENAME


@dataclass(frozen=True)
class CasePaths:
    root: Path
    slug: str

    @property
    def case_dir(self) -> Path:
        return case_dir(self.root, self.slug)

    @property
    def metadata_path(self) -> Path:
        return self.case_dir / CASE_METADATA_FILENAME


def list_case_dirs(case_studies_root: Path) -> list[Path]:
    """List immediate child directories that look like cases."""
    if not case_studies_root.exists():
        return []
    out: list[Path] = []
    for p in sorted(case_studies_root.iterdir()):
        if p.is_dir() and (p / CASE_METADATA_FILENAME).is_file():
            out.append(p)
    return out


def assert_within_root(root: Path, path: Path) -> None:
    """Raise ValueError if *path* is not inside *root* (after resolve)."""
    r = root.resolve()
    p = path.resolve()
    try:
        p.relative_to(r)
    except Exception as e:
        raise ValueError(f"path escapes root: {p} not within {r}") from e

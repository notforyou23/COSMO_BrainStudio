from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def project_root(start: Optional[Path] = None) -> Path:
    """Best-effort project root discovery for consistent artifact paths."""
    here = (start or Path(__file__)).resolve()
    for p in [here, *here.parents]:
        if (p / "pyproject.toml").is_file() or (p / ".git").exists():
            return p
        if (p / "runtime").is_dir() or (p / "outputs").is_dir():
            return p
    return here.parents[2] if len(here.parents) >= 3 else here.parent


def artifact_root(root: Optional[Path] = None, create: bool = True) -> Path:
    """Return artifact directory, preferring outputs/tools else runtime/_build.

    Override via COSMO_ARTIFACT_DIR (absolute or relative to project root).
    """
    root = project_root(root)
    override = os.environ.get("COSMO_ARTIFACT_DIR", "").strip()
    if override:
        p = Path(override)
        base = p if p.is_absolute() else (root / p)
    else:
        tools = root / "outputs" / "tools"
        base = tools if tools.is_dir() else (root / "runtime" / "_build")
    if create:
        base.mkdir(parents=True, exist_ok=True)
    return base


def _clean_stem(stem: str) -> str:
    s = (stem or "").strip().replace("\\", "_").replace("/", "_")
    return "".join(c for c in s if c.isalnum() or c in ("-", "_", ".", "+")) or "artifact"


def artifact_dir(subdir: Optional[str] = None, root: Optional[Path] = None, create: bool = True) -> Path:
    base = artifact_root(root=root, create=create)
    if not subdir:
        return base
    d = base / subdir
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def artifact_path(
    stem: str,
    suffix: str = ".json",
    *,
    subdir: Optional[str] = None,
    root: Optional[Path] = None,
    create_dirs: bool = True,
) -> Path:
    """Return a deterministic artifact file path under the selected artifact root."""
    d = artifact_dir(subdir=subdir, root=root, create=create_dirs)
    suf = suffix if suffix.startswith(".") or suffix == "" else f".{suffix}"
    return d / f"{_clean_stem(stem)}{suf}"


def write_artifact_text(
    stem: str,
    text: str,
    suffix: str = ".txt",
    *,
    subdir: Optional[str] = None,
    root: Optional[Path] = None,
    encoding: str = "utf-8",
) -> Path:
    p = artifact_path(stem, suffix=suffix, subdir=subdir, root=root, create_dirs=True)
    p.write_text(text, encoding=encoding)
    return p


def write_artifact_json(
    stem: str,
    obj,
    *,
    subdir: Optional[str] = None,
    root: Optional[Path] = None,
    indent: int = 2,
) -> Path:
    import json

    p = artifact_path(stem, suffix=".json", subdir=subdir, root=root, create_dirs=True)
    p.write_text(json.dumps(obj, indent=indent, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return p

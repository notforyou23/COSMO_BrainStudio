from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple


DEFAULT_REPORT_NAME = "DRAFT_REPORT_v0.md"
_DEFAULT_TEXT_MAX_BYTES = 5 * 1024 * 1024
_DEFAULT_BIN_MAX_BYTES = 25 * 1024 * 1024


class QAIOError(RuntimeError):
    pass


def canonicalize(path: Path | str, base_dir: Optional[Path] = None) -> Path:
    p = Path(path).expanduser()
    if not p.is_absolute():
        p = (base_dir or Path.cwd()) / p
    return p.resolve(strict=False)


def _is_hidden_or_system(p: Path) -> bool:
    parts = p.parts
    return any(part.startswith(".") for part in parts) or any(part in {"__pycache__", "node_modules", ".git"} for part in parts)


def safe_read_text(path: Path | str, *, encoding: str = "utf-8", max_bytes: int = _DEFAULT_TEXT_MAX_BYTES) -> str:
    p = canonicalize(path)
    try:
        st = p.stat()
    except FileNotFoundError as e:
        raise QAIOError(f"Missing file: {p}") from e
    if st.st_size > max_bytes:
        raise QAIOError(f"Refusing to read large text file ({st.st_size} bytes > {max_bytes}): {p}")
    data = p.read_bytes()
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def safe_read_bytes(path: Path | str, *, max_bytes: int = _DEFAULT_BIN_MAX_BYTES) -> bytes:
    p = canonicalize(path)
    try:
        st = p.stat()
    except FileNotFoundError as e:
        raise QAIOError(f"Missing file: {p}") from e
    if st.st_size > max_bytes:
        raise QAIOError(f"Refusing to read large binary file ({st.st_size} bytes > {max_bytes}): {p}")
    return p.read_bytes()


def _candidate_roots(start_dir: Path) -> Iterable[Path]:
    d = canonicalize(start_dir)
    seen = set()
    for _ in range(25):
        if d in seen:
            break
        seen.add(d)
        yield d
        if d.parent == d:
            break
        d = d.parent
def find_report_path(start_dir: Path | str = ".", report_name: str = DEFAULT_REPORT_NAME) -> Path:
    sd = canonicalize(start_dir)
    # fast paths
    for root in _candidate_roots(sd):
        direct = root / report_name
        if direct.is_file():
            return direct.resolve(strict=False)
        for sub in ("reports", "report", "docs", "doc", "outputs"):
            p = root / sub / report_name
            if p.is_file():
                return p.resolve(strict=False)

    # bounded recursive search (skip hidden/system dirs)
    roots = list(_candidate_roots(sd))
    best: Optional[Path] = None
    best_depth = 10**9
    for root in roots[:3]:  # limit breadth
        try:
            for p in root.rglob(report_name):
                if _is_hidden_or_system(p):
                    continue
                if p.is_file():
                    try:
                        depth = len(p.relative_to(root).parts)
                    except Exception:
                        depth = len(p.parts)
                    if depth < best_depth:
                        best, best_depth = p, depth
                        if best_depth <= 2:
                            return best.resolve(strict=False)
        except Exception:
            continue
    if best:
        return best.resolve(strict=False)
    raise QAIOError(f"Could not locate {report_name} starting from: {sd}")


def discover_pilot_artifacts(
    start_dir: Path | str = ".",
    *,
    include_exts: Sequence[str] = (".json", ".csv", ".tsv", ".md", ".txt", ".png", ".jpg", ".jpeg", ".pdf", ".parquet", ".xlsx"),
    max_files: int = 500,
) -> list[Path]:
    sd = canonicalize(start_dir)
    roots = list(_candidate_roots(sd))
    dir_names = ("pilot_artifacts", "pilot", "artifacts", "artifact", "outputs", "data")
    candidates: list[Path] = []
    for root in roots[:3]:
        for dn in dir_names:
            d = root / dn
            if d.is_dir():
                candidates.append(d)
    if not candidates:
        candidates.append(sd)

    found: list[Path] = []
    exts = {e.lower() for e in include_exts}
    for base in candidates:
        try:
            for p in base.rglob("*"):
                if len(found) >= max_files:
                    break
                if _is_hidden_or_system(p):
                    continue
                if p.is_file() and (not exts or p.suffix.lower() in exts):
                    found.append(p.resolve(strict=False))
        except Exception:
            continue
        if len(found) >= max_files:
            break
    # de-dup stable
    uniq: dict[str, Path] = {}
    for p in found:
        uniq.setdefault(str(p), p)
    return sorted(uniq.values(), key=lambda x: str(x))


@dataclass(frozen=True)
class Inputs:
    report_path: Path
    report_text: str
    artifact_paths: Tuple[Path, ...]


def load_inputs(
    start_dir: Path | str = ".",
    *,
    report_name: str = DEFAULT_REPORT_NAME,
    artifact_exts: Sequence[str] = (".json", ".csv", ".tsv", ".md", ".txt"),
    max_report_bytes: int = _DEFAULT_TEXT_MAX_BYTES,
    max_artifacts: int = 500,
) -> Inputs:
    rp = find_report_path(start_dir, report_name=report_name)
    rt = safe_read_text(rp, max_bytes=max_report_bytes)
    arts = discover_pilot_artifacts(start_dir, include_exts=artifact_exts, max_files=max_artifacts)
    # avoid double-counting the report if it lives within artifact dir
    arts = [p for p in arts if p.resolve(strict=False) != rp.resolve(strict=False)]
    return Inputs(report_path=rp, report_text=rt, artifact_paths=tuple(arts))


def relpath(path: Path | str, base_dir: Path | str = ".") -> str:
    p = canonicalize(path)
    b = canonicalize(base_dir)
    try:
        return str(p.relative_to(b))
    except Exception:
        return str(p)

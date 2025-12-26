from __future__ import annotations
import argparse
import fnmatch
import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple, Optional

REPL_FROM_POSIX = "runtime/outputs/"
REPL_FROM_WIN = "runtime\\outputs\\"
REPL_TO_POSIX = "outputs/"
REPL_TO_WIN = "outputs\\"

@dataclass
class SyncItem:
    src: Path
    dst: Path
    action: str  # copied|duplicate_same|conflict
    note: str = ""

def _repo_root() -> Path:
    # src/cli/path_canonicalize.py -> repo root is parents[2]
    return Path(__file__).resolve().parents[2]

def _iter_files(base: Path) -> Iterable[Path]:
    if not base.exists():
        return
    for p in base.rglob("*"):
        if p.is_file():
            yield p

def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _ensure_parent(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)

def sync_runtime_outputs_to_outputs(runtime_outputs: Path, outputs: Path, *, dry_run: bool = False) -> List[SyncItem]:
    items: List[SyncItem] = []
    if not runtime_outputs.exists():
        return items
    for src in _iter_files(runtime_outputs):
        rel = src.relative_to(runtime_outputs)
        dst = outputs / rel
        if dst.exists():
            try:
                same = (src.stat().st_size == dst.stat().st_size) and (_sha256(src) == _sha256(dst))
            except OSError:
                same = False
            if same:
                items.append(SyncItem(src, dst, "duplicate_same", "already identical"))
                continue
            items.append(SyncItem(src, dst, "conflict", "destination exists with different content"))
            continue
        items.append(SyncItem(src, dst, "copied", "synced from runtime/outputs"))
        if not dry_run:
            _ensure_parent(dst)
            shutil.copy2(src, dst)
    return items

def _is_text_file(p: Path, max_bytes: int = 2_000_000) -> bool:
    try:
        data = p.read_bytes()
    except OSError:
        return False
    if len(data) > max_bytes:
        return False
    if b"\x00" in data:
        return False
    return True

def _matches_any(path_str: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(path_str, pat) for pat in patterns)

def rewrite_references(repo_root: Path, *, dry_run: bool = False,
                      allow_globs: Optional[List[str]] = None,
                      deny_globs: Optional[List[str]] = None) -> List[Tuple[Path, int]]:
    allow_globs = allow_globs or ["**/*.md", "**/*.txt", "**/*.py", "**/*.json", "**/*.yaml", "**/*.yml", "**/*.toml"]
    deny_globs = deny_globs or ["outputs/**", "runtime/outputs/**", ".git/**", "**/__pycache__/**", "**/*.png", "**/*.jpg", "**/*.jpeg", "**/*.pdf"]
    changes: List[Tuple[Path, int]] = []
    for p in repo_root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(repo_root).as_posix()
        if _matches_any(rel, deny_globs):
            continue
        if not _matches_any(rel, allow_globs):
            continue
        if not _is_text_file(p):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = text.replace(REPL_FROM_POSIX, REPL_TO_POSIX).replace(REPL_FROM_WIN, REPL_TO_WIN)
        if new != text:
            n = text.count(REPL_FROM_POSIX) + text.count(REPL_FROM_WIN)
            changes.append((p, n))
            if not dry_run:
                p.write_text(new, encoding="utf-8")
    return changes

def _md_table(rows: List[Tuple[str, str, str]]) -> str:
    if not rows:
        return "_(none)_\n"
    out = ["| Source | Destination | Action |", "|---|---|---|"]
    out += [f"| `{s}` | `{d}` | {a} |" for (s, d, a) in rows]
    return "\n".join(out) + "\n"

def write_report(report_path: Path, *, repo_root: Path, runtime_outputs: Path, outputs: Path,
                 synced: List[SyncItem], rewrites: List[Tuple[Path, int]], dry_run: bool) -> None:
    _ensure_parent(report_path)
    moved = [i for i in synced if i.action == "copied"]
    dups = [i for i in synced if i.action == "duplicate_same"]
    conflicts = [i for i in synced if i.action == "conflict"]
    def rel(p: Path) -> str:
        try:
            return p.relative_to(repo_root).as_posix()
        except Exception:
            return str(p)
    lines = []
    lines.append("# Path Canonicalization Report\n")
    lines.append(f"- Repo root: `{repo_root}`")
    lines.append(f"- Runtime outputs scanned: `{runtime_outputs}`")
    lines.append(f"- Canonical outputs: `{outputs}`")
    lines.append(f"- Dry run: `{dry_run}`\n")
    lines.append("## Sync summary\n")
    lines.append(f"- Copied: **{len(moved)}**")
    lines.append(f"- Duplicates (same content, already present): **{len(dups)}**")
    lines.append(f"- Conflicts (destination exists, different content): **{len(conflicts)}**\n")
    rows = [(rel(i.src), rel(i.dst), i.action) for i in synced]
    lines.append("### Files considered\n")
    lines.append(_md_table(rows))
    lines.append("\n## Reference rewrites\n")
    lines.append(f"- Files modified: **{len(rewrites)}**\n")
    if rewrites:
        rrows = [(rel(p), rel(p), f"replaced {n} occurrence(s)") for (p, n) in rewrites]
        lines.append(_md_table([(a, b, c) for (a, b, c) in rrows]))
    else:
        lines.append("_(none)_\n")
    lines.append("\n## Notes\n")
    lines.append(f"- Canonicalization rewrites only replace `{REPL_FROM_POSIX}`/`{REPL_FROM_WIN}` with `{REPL_TO_POSIX}`/`{REPL_TO_WIN}`.")
    lines.append("- Conflicts are reported but never overwritten by this command.\n")
    report_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="path-canonicalize", description="Sync runtime/outputs into canonical outputs and optionally rewrite references.")
    ap.add_argument("--repo-root", default=None, help="Repository root (default: auto-detect from this file).")
    ap.add_argument("--runtime-outputs", default="runtime/outputs", help="Runtime outputs directory relative to repo root.")
    ap.add_argument("--outputs", default="outputs", help="Canonical outputs directory relative to repo root.")
    ap.add_argument("--report", default="outputs/qa/path_canonicalization_report.md", help="Report path relative to repo root.")
    ap.add_argument("--rewrite", action="store_true", help="Rewrite in-repo references from runtime/outputs to outputs.")
    ap.add_argument("--dry-run", action="store_true", help="Do not copy or rewrite; only report.")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve() if args.repo_root else _repo_root()
    runtime_outputs = (repo_root / args.runtime_outputs).resolve()
    outputs = (repo_root / args.outputs).resolve()
    report_path = (repo_root / args.report).resolve()

    synced = sync_runtime_outputs_to_outputs(runtime_outputs, outputs, dry_run=args.dry_run)
    rewrites: List[Tuple[Path, int]] = []
    if args.rewrite:
        rewrites = rewrite_references(repo_root, dry_run=args.dry_run)

    if not args.dry_run:
        (outputs / "qa").mkdir(parents=True, exist_ok=True)
    write_report(report_path, repo_root=repo_root, runtime_outputs=runtime_outputs, outputs=outputs,
                 synced=synced, rewrites=rewrites, dry_run=args.dry_run)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

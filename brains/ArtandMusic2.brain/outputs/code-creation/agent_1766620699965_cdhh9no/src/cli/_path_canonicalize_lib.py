from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import fnmatch, hashlib, os, re
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

TEXT_EXTS = {".md",".txt",".json",".yaml",".yml",".toml",".csv",".tsv",".py",".js",".ts",".html",".css",".xml",".ini",".cfg",".rst",".sql",".sh",".bat",".ps1"}

@dataclass(frozen=True)
class CopyAction:
    src: str
    dst: str
    status: str  # copied|skipped_identical|skipped_conflict|error
    reason: str = ""

@dataclass(frozen=True)
class RewriteAction:
    path: str
    status: str  # rewritten|skipped|error
    replacements: int = 0
    reason: str = ""


def iter_files(root: Path, exclude_dirs: Sequence[str] = (".git","__pycache__")) -> Iterator[Path]:
    root = Path(root)
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in exclude_dirs and not d.startswith(".")]
        for fn in fns:
            p = Path(dp) / fn
            if p.is_file():
                yield p


def file_hash(path: Path, algo: str = "sha256", chunk: int = 1024 * 1024) -> str:
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def relative_under(path: Path, root: Path) -> Optional[Path]:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve())
    except Exception:
        return None


def sync_tree(src_root: Path, dst_root: Path, *, dry_run: bool = False) -> Tuple[List[CopyAction], Dict[str, List[str]]]:
    actions: List[CopyAction] = []
    dups: Dict[str, List[str]] = {}  # hash -> [paths...]
    src_root, dst_root = Path(src_root), Path(dst_root)
    for src in iter_files(src_root):
        rel = relative_under(src, src_root)
        if rel is None:
            continue
        dst = dst_root / rel
        try:
            sh = file_hash(src)
            dups.setdefault(sh, []).append(str(src))
            if dst.exists():
                dh = file_hash(dst)
                dups.setdefault(dh, []).append(str(dst))
                if dh == sh:
                    actions.append(CopyAction(str(src), str(dst), "skipped_identical"))
                    continue
                actions.append(CopyAction(str(src), str(dst), "skipped_conflict", "destination exists with different content"))
                continue
            actions.append(CopyAction(str(src), str(dst), "copied"))
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                with open(src, "rb") as r, open(dst, "wb") as w:
                    for b in iter(lambda: r.read(1024 * 1024), b""):
                        w.write(b)
        except Exception as e:
            actions.append(CopyAction(str(src), str(dst), "error", str(e)))
    return actions, dups


def duplicates_summary(dups: Dict[str, List[str]], *, min_copies: int = 2) -> Dict[str, List[str]]:
    return {h: sorted(set(ps)) for h, ps in dups.items() if len(set(ps)) >= min_copies}


def should_rewrite(path: Path, allow_globs: Sequence[str], deny_globs: Sequence[str]) -> bool:
    s = str(path).replace("\\", "/")
    if any(fnmatch.fnmatch(s, g) for g in deny_globs):
        return False
    return (not allow_globs) or any(fnmatch.fnmatch(s, g) for g in allow_globs)


def rewrite_references(repo_root: Path, *, old: str, new: str, dry_run: bool = False,
                       allow_globs: Sequence[str] = (), deny_globs: Sequence[str] = ("*/.git/*","*/__pycache__/*","*/.venv/*","*/venv/*","*/node_modules/*")) -> List[RewriteAction]:
    repo_root = Path(repo_root)
    actions: List[RewriteAction] = []
    old_norm = old.replace("\\","/")
    new_norm = new.replace("\\","/")
    pat = re.compile(re.escape(old_norm))
    for p in iter_files(repo_root, exclude_dirs=(".git","__pycache__","node_modules",".venv","venv")):
        rel = relative_under(p, repo_root)
        if rel is None or not should_rewrite(rel, allow_globs, deny_globs):
            continue
        if p.suffix.lower() not in TEXT_EXTS:
            actions.append(RewriteAction(str(rel), "skipped", 0, "non-text extension"))
            continue
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            actions.append(RewriteAction(str(rel), "skipped", 0, "unreadable as utf-8"))
            continue
        if old_norm not in txt and old not in txt:
            actions.append(RewriteAction(str(rel), "skipped", 0, "no matches"))
            continue
        txt2, n = pat.subn(new_norm, txt.replace(old, old_norm))
        actions.append(RewriteAction(str(rel), "rewritten" if n else "skipped", n, "" if n else "no matches"))
        if n and not dry_run:
            p.write_text(txt2, encoding="utf-8")
    return actions


def generate_markdown_report(copy_actions: Sequence[CopyAction], dup_map: Dict[str, List[str]],
                             rewrite_actions: Sequence[RewriteAction] = (), *, title: str = "Path canonicalization report") -> str:
    copied = [a for a in copy_actions if a.status == "copied"]
    ident = [a for a in copy_actions if a.status == "skipped_identical"]
    confl = [a for a in copy_actions if a.status == "skipped_conflict"]
    errs = [a for a in copy_actions if a.status == "error"]
    dups = duplicates_summary(dup_map)
    rew = [a for a in rewrite_actions if a.status == "rewritten"]
    rerrs = [a for a in rewrite_actions if a.status == "error"]
    lines = [f"# {title}",
             "",
             "## Summary",
             f"- Copied: {len(copied)}",
             f"- Skipped (identical): {len(ident)}",
             f"- Skipped (conflict): {len(confl)}",
             f"- Errors: {len(errs)}",
             f"- Duplicate-content groups: {len(dups)}",
             f"- Rewritten files: {len(rew)}",
             f"- Rewrite errors: {len(rerrs)}",
             "",
             "## Copy / sync actions",
             "| status | src | dst | reason |",
             "|---|---|---|---|"]
    for a in copy_actions:
        lines.append(f"| {a.status} | `{a.src}` | `{a.dst}` | {a.reason or ''} |")
    lines += ["", "## Duplicate detection (by content hash)"]
    if not dups:
        lines.append("_No duplicate-content groups detected._")
    else:
        for h, ps in sorted(dups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            lines.append(f"- `{h}` ({len(ps)} files)")
            for p in ps:
                lines.append(f"  - `{p}`")
    if rewrite_actions:
        lines += ["", "## Reference rewriting", "| status | path | replacements | reason |", "|---|---|---:|---|"]
        for a in rewrite_actions:
            lines.append(f"| {a.status} | `{a.path}` | {a.replacements} | {a.reason or ''} |")
    return "\n".join(lines) + "\n"

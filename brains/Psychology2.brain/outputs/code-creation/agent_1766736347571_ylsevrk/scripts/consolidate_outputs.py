from __future__ import annotations
import argparse
import hashlib
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def _iter_agent_outputs(root: Path):
    out_dirs = set()
    for pat in ("code-creation/**/outputs", "agent*/**/outputs", "**/outputs"):
        for d in root.glob(pat):
            if not d.is_dir():
                continue
            try:
                rel = d.relative_to(root)
            except ValueError:
                continue
            if rel.parts and rel.parts[0] == "outputs":
                continue
            if "node_modules" in rel.parts or ".git" in rel.parts:
                continue
            out_dirs.add(d)
    for d in sorted(out_dirs, key=lambda p: str(p).lower()):
        for f in sorted(d.rglob("*"), key=lambda p: str(p).lower()):
            if f.is_file():
                yield d, f

def _rel_under_outputs(out_dir: Path, f: Path) -> Path:
    rel = f.relative_to(out_dir)
    return rel

def consolidate(root: Path, outputs: Path, overwrite: bool, dry_run: bool, update_changelog: bool):
    outputs.mkdir(parents=True, exist_ok=True)
    candidates = {}  # dest_rel -> list[src]
    for out_dir, f in _iter_agent_outputs(root):
        dest_rel = _rel_under_outputs(out_dir, f)
        if dest_rel.parts and dest_rel.parts[0].startswith("."):
            continue
        candidates.setdefault(dest_rel.as_posix(), []).append(f)

    actions = []
    for dest_rel, srcs in sorted(candidates.items(), key=lambda kv: kv[0].lower()):
        dest = outputs / dest_rel
        srcs_sorted = sorted(srcs, key=lambda p: str(p).lower())
        chosen = srcs_sorted[0]
        if dest.exists():
            try:
                same = (dest.stat().st_size == chosen.stat().st_size) and (_sha256(dest) == _sha256(chosen))
            except OSError:
                same = False
            if same:
                continue
            if not overwrite:
                continue
        actions.append((chosen, dest))

    for src, dest in actions:
        if dry_run:
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass
        shutil.copy2(src, tmp)
        os.replace(tmp, dest)

    if update_changelog and actions and not dry_run:
        changelog = root / "CHANGELOG.md"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        lines = [f"\n## {ts} Consolidated agent outputs\n"]
        for src, dest in actions:
            try:
                rel = dest.relative_to(root).as_posix()
            except ValueError:
                rel = dest.as_posix()
            lines.append(f"- {rel} (from {src.as_posix()})\n")
        if changelog.exists():
            prior = changelog.read_text(encoding="utf-8")
        else:
            prior = "# Changelog\n"
        changelog.write_text(prior.rstrip("\n") + "".join(lines) + "\n", encoding="utf-8")

    return actions

def main():
    ap = argparse.ArgumentParser(description="Consolidate agent-produced artifacts into canonical outputs/ scaffold.")
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="Project root (default: repo root).")
    ap.add_argument("--outputs", type=Path, default=None, help="Canonical outputs dir (default: <root>/outputs).")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite differing existing canonical files.")
    ap.add_argument("--dry-run", action="store_true", help="Do not write files; compute planned actions only.")
    ap.add_argument("--update-changelog", action="store_true", help="Append a consolidation entry to CHANGELOG.md.")
    args = ap.parse_args()

    root = args.root.resolve()
    outputs = (args.outputs or (root / "outputs")).resolve()
    actions = consolidate(root, outputs, args.overwrite, args.dry_run, args.update_changelog)
    print(f"CONSOLIDATED:{len(actions)}")
    if args.dry_run and actions:
        for src, dest in actions[:50]:
            print(f"PLAN:{src.as_posix()} -> {dest.as_posix()}")

if __name__ == "__main__":
    main()

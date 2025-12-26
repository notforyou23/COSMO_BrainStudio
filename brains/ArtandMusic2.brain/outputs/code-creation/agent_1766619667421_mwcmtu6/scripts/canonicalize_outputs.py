#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve()
for _ in range(8):
    if (REPO_ROOT / "runtime" / "outputs").exists():
        break
    if REPO_ROOT.parent == REPO_ROOT:
        break
    REPO_ROOT = REPO_ROOT.parent
RUNTIME_OUT = REPO_ROOT / "runtime" / "outputs"
CANON_ROOT = RUNTIME_OUT / "canonical"
TRACKER = RUNTIME_OUT / "PROJECT_TRACKER.json"
REPORT = RUNTIME_OUT / "CANONICALIZATION_REPORT.md"

def sha1_file(p: Path, chunk=1024 * 1024) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

def is_agent_deliverable(p: Path) -> bool:
    if not p.is_file(): return False
    if "__pycache__" in p.parts or p.suffix in {".pyc", ".pyo"}: return False
    rel = p.resolve().relative_to(REPO_ROOT) if p.resolve().is_relative_to(REPO_ROOT) else None
    if rel and rel.parts[:2] == ("runtime","outputs"): return False
    parts = set(p.parts)
    return any(x in parts for x in ("code-creation","document-creation")) or any(s.startswith("agent_") for s in p.parts)

def category_for(p: Path) -> str:
    parts = set(p.parts)
    if "document-creation" in parts or p.suffix.lower() in {".md",".pdf",".docx",".txt"}: return "documents"
    if "code-creation" in parts or p.suffix.lower() in {".py",".ipynb",".js",".ts",".sh"}: return "code"
    return "misc"

def dest_for(src: Path) -> Path:
    rel = src.resolve().relative_to(REPO_ROOT) if src.resolve().is_relative_to(REPO_ROOT) else Path(src.name)
    cat = category_for(src)
    stem = rel.name
    base = CANON_ROOT / cat / stem
    if not base.exists(): return base
    try:
        same = base.is_file() and base.stat().st_size == src.stat().st_size and sha1_file(base) == sha1_file(src)
        if same: return base
    except Exception:
        pass
    h = hashlib.sha1(rel.as_posix().encode("utf-8")).hexdigest()[:10]
    return base.with_name(f"{base.stem}-{h}{base.suffix}")

def migrate(files: list[Path], move: bool, dry_run: bool):
    mappings, actions = [], []
    for src in files:
        dst = dest_for(src)
        dst.parent.mkdir(parents=True, exist_ok=True)
        action = "skip"
        if dst.exists():
            try:
                if dst.stat().st_size == src.stat().st_size and sha1_file(dst) == sha1_file(src):
                    action = "skip"
                else:
                    action = "copy" if not move else "move"
            except Exception:
                action = "copy" if not move else "move"
        else:
            action = "copy" if not move else "move"
        if not dry_run and action in ("copy","move"):
            if move: shutil.move(str(src), str(dst))
            else: shutil.copy2(src, dst)
        mappings.append((src, dst))
        actions.append(action)
    return mappings, actions

def rewrite_tracker(mappings: list[tuple[Path,Path]], dry_run: bool) -> tuple[int,int]:
    if not TRACKER.exists(): return (0,0)
    data_txt = TRACKER.read_text(encoding="utf-8")
    try:
        data = json.loads(data_txt)
    except Exception:
        return (0,0)
    map_str = {}
    for o,n in mappings:
        if not o.resolve().is_relative_to(REPO_ROOT) or not n.resolve().is_relative_to(REPO_ROOT): continue
        orel = o.resolve().relative_to(REPO_ROOT).as_posix()
        nrel = n.resolve().relative_to(REPO_ROOT).as_posix()
        map_str[orel] = nrel
        map_str[str((REPO_ROOT / orel).resolve())] = nrel

    def walk(x):
        changed = 0
        if isinstance(x, dict):
            out = {}
            for k,v in x.items():
                nv,c = walk(v); changed += c; out[k] = nv
            return out, changed
        if isinstance(x, list):
            out = []
            for v in x:
                nv,c = walk(v); changed += c; out.append(nv)
            return out, changed
        if isinstance(x, str):
            if x in map_str: return map_str[x], 1
            # common cases: stored as relative or embedded path-like string
            for orel,nrel in map_str.items():
                if x.endswith(orel) and ("/" in orel or "\" in orel):
                    return x[:-len(orel)] + nrel, 1
            return x, 0
        return x, 0

    new_data, changed = walk(data)
    if not dry_run and changed:
        TRACKER.write_text(json.dumps(new_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return (1, changed)

def write_report(mappings, actions, dry_run: bool):
    moved = sum(1 for a in actions if a=="move")
    copied = sum(1 for a in actions if a=="copy")
    skipped = sum(1 for a in actions if a=="skip")
    lines = []
    lines += ["# Canonicalization Report",""]
    lines += [f"- Repository root: `{REPO_ROOT}`"]
    lines += [f"- Canonical root: `{CANON_ROOT}`"]
    lines += [f"- Dry run: `{dry_run}`",""]
    lines += [f"## Summary","",f"- Discovered: `{len(mappings)}`",f"- Copied: `{copied}`",f"- Moved: `{moved}`",f"- Skipped (already canonical/identical): `{skipped}`",""]
    lines += ["## Mappings","", "| Action | Old path | New canonical path |","|---|---|---|"]
    for (o,n),a in sorted(zip(mappings, actions), key=lambda t: str(t[0][0])):
        def rel(p: Path):
            try: return p.resolve().relative_to(REPO_ROOT).as_posix()
            except Exception: return str(p)
        lines.append(f"| {a} | `{rel(o)}` | `{rel(n)}` |")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Canonicalize and migrate agent-specific deliverables into runtime/outputs/")
    ap.add_argument("--move", action="store_true", help="Move instead of copy")
    ap.add_argument("--dry-run", action="store_true", help="Plan only; do not write/copy/move")
    args = ap.parse_args()

    # discover
    files = []
    for p in REPO_ROOT.rglob("*"):
        if is_agent_deliverable(p):
            files.append(p)
    mappings, actions = migrate(files, move=args.move, dry_run=args.dry_run)
    tracker_seen, tracker_changed = rewrite_tracker(mappings, dry_run=args.dry_run)
    write_report(mappings, actions, dry_run=args.dry_run)

    # validate referenced canonical files exist (best-effort)
    missing = sum(1 for _,dst in mappings if not args.dry_run and not dst.exists())
    print(f"STATUS:discovered={len(files)} copied={actions.count('copy')} moved={actions.count('move')} skipped={actions.count('skip')} tracker_updated={tracker_changed} missing_after={missing}")

if __name__ == "__main__":
    main()

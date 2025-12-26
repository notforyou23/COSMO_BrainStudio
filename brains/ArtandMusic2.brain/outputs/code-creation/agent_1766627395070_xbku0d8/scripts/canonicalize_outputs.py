#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT_DEFAULT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Cand:
    path: Path
    score: float
    reason: str

def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def _rel(root: Path, p: Path) -> str:
    try: return str(p.resolve().relative_to(root.resolve()))
    except Exception: return str(p)

def _walk_files(root: Path) -> list[Path]:
    ign = {'.git', '__pycache__', '.venv', 'venv', 'node_modules', '.pytest_cache', '.mypy_cache'}
    out = (root / 'outputs').resolve()
    files = []
    for dp, dn, fn in os.walk(root):
        dpath = Path(dp)
        dn[:] = [d for d in dn if d not in ign and not (dpath / d).resolve().samefile(out) if (dpath / d).exists() else d not in ign]
        if dpath.resolve() == out:  # don't scan canonical outputs
            dn[:] = []
            continue
        for f in fn:
            p = dpath / f
            if p.is_file():
                files.append(p)
    return sorted(files, key=lambda p: (_rel(root, p).lower(), p.stat().st_mtime))

def _score_qa(root: Path, p: Path) -> Cand | None:
    name = p.name.lower()
    if p.suffix.lower() not in {'.py', '.sh', '.bash'}: return None
    if not (('qa' in name and 'run' in name) or name in {'qa.py','qa.sh','run_qa.py','run_qa.sh'}): return None
    try:
        txt = p.read_text(encoding='utf-8', errors='ignore')[:20000]
    except Exception:
        txt = ''
    s = 0.0; r = []
    rel = _rel(root, p).lower()
    if rel.startswith('scripts/'): s += 4; r.append('in scripts/')
    if 'pytest' in txt or 'unittest' in txt: s += 3; r.append('test runner keywords')
    if 'argparse' in txt or '--help' in txt: s += 1; r.append('cli-like')
    if name in {'qa_run.py','qa_run.sh'}: s += 2; r.append('canonical name')
    if 'stage' in rel or 'attempt' in rel or 'introspection' in rel: s -= 2; r.append('agent/runtime-ish')
    try:
        age = (datetime.now().timestamp() - p.stat().st_mtime)
        s += max(0.0, 3.0 - age / (24*3600))  # up to +3 for <1 day old
    except Exception:
        pass
    return Cand(p, s, '; '.join(r) or 'name match')

def _looks_like_schema(obj) -> bool:
    if not isinstance(obj, dict): return False
    if '$schema' in obj: return True
    if obj.get('type') in {'object','array','string','number','integer','boolean','null'}: return True
    if 'properties' in obj or 'items' in obj: return True
    return False

def _score_schema(root: Path, p: Path) -> Cand | None:
    name = p.name.lower()
    if p.suffix.lower() != '.json': return None
    if 'schema' not in name: return None
    try:
        obj = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None
    if not _looks_like_schema(obj): return None
    s = 0.0; r = []
    rel = _rel(root, p).lower()
    if rel.startswith('schemas/') or '/schemas/' in rel: s += 5; r.append('in schemas/')
    if rel.startswith('outputs/'): s -= 1; r.append('already in outputs/')
    if name in {'output_schema.json','outputs_schema.json','schema.json'}: s += 2; r.append('canonical name')
    if 'draft' in json.dumps(obj)[:400].lower(): s += 1; r.append('draft indicated')
    if 'stage' in rel or 'attempt' in rel or 'introspection' in rel: s -= 2; r.append('agent/runtime-ish')
    try:
        age = (datetime.now().timestamp() - p.stat().st_mtime)
        s += max(0.0, 3.0 - age / (24*3600))
    except Exception:
        pass
    return Cand(p, s, '; '.join(r) or 'schema-like')

def _pick_best(cands: list[Cand]) -> Cand | None:
    if not cands: return None
    cands = sorted(cands, key=lambda c: (-c.score, _rel(ROOT_DEFAULT, c.path).lower()))
    return cands[0]

def _copy_unique(src: Path, dst_dir: Path, preferred_name: str | None = None, dry: bool = False) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    base = preferred_name or src.name
    dst = dst_dir / base
    if dst.exists():
        try:
            if dst.is_file() and _sha256(dst) == _sha256(src):
                return dst
        except Exception:
            pass
        stem, suf = dst.stem, dst.suffix
        for i in range(2, 1000):
            cand = dst_dir / f'{stem}_{i}{suf}'
            if not cand.exists():
                dst = cand
                break
    if not dry:
        shutil.copy2(src, dst)
        if dst.suffix.lower() in {'.sh', '.bash'}:
            try: dst.chmod(dst.stat().st_mode | 0o111)
            except Exception: pass
    return dst

def _write_index(root: Path, canonical_dir: Path, picks: dict[str, tuple[Path, str]], dry: bool = False) -> Path:
    out = root / 'outputs'
    out.mkdir(parents=True, exist_ok=True)
    idx = out / 'ARTIFACT_INDEX.md'
    lines = []
    lines.append('# Artifact Index (Canonical)')
    lines.append('')
    lines.append(f'Generated: {datetime.now().isoformat(timespec="seconds")}')
    lines.append('')
    lines.append('## Authoritative picks')
    for k in ('qa_runner', 'schema'):
        if k in picks:
            p, reason = picks[k]
            lines.append(f'- **{k}**: `{_rel(root, p)}`  ')
            lines.append(f'  - reason: {reason}')
    lines.append('')
    lines.append('## Canonical outputs tree')
    files = [p for p in sorted(canonical_dir.rglob('*')) if p.is_file()]
    if not files:
        lines.append('- (empty)')
    else:
        for p in files:
            if p.name == 'ARTIFACT_INDEX.md': continue
            lines.append(f'- `{_rel(root, p)}`')
    lines.append('')
    txt = '\n'.join(lines) + '\n'
    if not dry:
        idx.write_text(txt, encoding='utf-8')
    return idx

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description='Canonicalize scattered deliverables into a single outputs/ tree.')
    ap.add_argument('--root', type=Path, default=ROOT_DEFAULT, help='Project root (default: repo root inferred from this script).')
    ap.add_argument('--dry-run', action='store_true', help='Do not write/copy anything.')
    ap.add_argument('--verbose', action='store_true', help='Print selection details.')
    args = ap.parse_args(argv)

    root = args.root.resolve()
    files = _walk_files(root)

    qa_cands = [c for p in files if (c := _score_qa(root, p)) is not None]
    sc_cands = [c for p in files if (c := _score_schema(root, p)) is not None]
    qa = _pick_best(qa_cands)
    schema = _pick_best(sc_cands)

    canonical = root / 'outputs' / 'canonical'
    picks: dict[str, tuple[Path, str]] = {}
    if qa:
        dst = _copy_unique(qa.path, canonical / 'qa', preferred_name=qa.path.name, dry=args.dry_run)
        picks['qa_runner'] = (dst, f'score={qa.score:.2f}; {qa.reason}; source={_rel(root, qa.path)}')
    if schema:
        dst = _copy_unique(schema.path, canonical / 'schema', preferred_name=schema.path.name, dry=args.dry_run)
        picks['schema'] = (dst, f'score={schema.score:.2f}; {schema.reason}; source={_rel(root, schema.path)}')

    _write_index(root, canonical, picks, dry=args.dry_run)

    if args.verbose:
        def _top(lst): return sorted(lst, key=lambda c: (-c.score, _rel(root, c.path).lower()))[:5]
        print('TOP_QA:', *[f'{c.score:.2f}:{_rel(root,c.path)}' for c in _top(qa_cands)], sep='\n  ')
        print('TOP_SCHEMA:', *[f'{c.score:.2f}:{_rel(root,c.path)}' for c in _top(sc_cands)], sep='\n  ')
        print('PICKS:', json.dumps({k: _rel(root, v[0]) for k, v in picks.items()}, indent=2))

    return 0 if qa and schema else 2

if __name__ == '__main__':
    raise SystemExit(main())

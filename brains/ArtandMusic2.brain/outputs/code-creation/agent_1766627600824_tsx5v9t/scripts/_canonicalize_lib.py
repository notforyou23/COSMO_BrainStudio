from __future__ import annotations
from pathlib import Path
import hashlib, json, os, re, shutil, time
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

TEXT_EXT = {'.md', '.txt', '.rst', '.log'}
DATA_EXT = {'.json', '.csv', '.tsv', '.parquet', '.yaml', '.yml'}
IMG_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
CODE_EXT = {'.py', '.sh', '.ipynb'}

def _norm(p: Path) -> str:
    return str(p).replace('\\', '/')

def discover_files(roots: Sequence[Path], include: Optional[Sequence[str]] = None,
                   exclude_dir_regex: str = r'(^|/)(\.git|__pycache__|node_modules)(/|$)') -> List[Path]:
    inc_re = [re.compile(x) for x in (include or [r'.*'])]
    ex = re.compile(exclude_dir_regex)
    out: List[Path] = []
    for r in roots:
        r = Path(r)
        if not r.exists():
            continue
        if r.is_file():
            out.append(r)
            continue
        for p in r.rglob('*'):
            if not p.is_file():
                continue
            s = _norm(p)
            if ex.search(s):
                continue
            name = p.name
            if any(rx.search(name) for rx in inc_re):
                out.append(p)
    return sorted(set(out))

def file_hash(p: Path, max_bytes: int = 2_000_000) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        remaining = max_bytes
        while remaining > 0:
            b = f.read(min(65536, remaining))
            if not b:
                break
            h.update(b)
            remaining -= len(b)
    return h.hexdigest()

def score_path(p: Path) -> float:
    try:
        st = p.stat()
    except FileNotFoundError:
        return -1.0
    score = 0.0
    score += min(st.st_size / 1024.0, 2000.0) * 0.01
    age = max(0.0, time.time() - st.st_mtime)
    score += max(0.0, 2000.0 - min(age, 2000.0)) * 0.001
    n = p.name.lower()
    for kw, bump in [('final', 1.5), ('best', 1.0), ('report', 0.8), ('canonical', 0.6), ('output', 0.3)]:
        if kw in n:
            score += bump
    if p.suffix.lower() in ('.md', '.json', '.csv', '.png', '.pdf'):
        score += 0.25
    return score

def suggest_dest_rel(src: Path) -> Path:
    ext = src.suffix.lower()
    if ext in CODE_EXT:
        base = Path('outputs') / 'artifacts' / 'code'
    elif ext in IMG_EXT:
        base = Path('outputs') / 'artifacts' / 'images'
    elif ext in DATA_EXT:
        base = Path('outputs') / 'artifacts' / 'data'
    elif ext in TEXT_EXT:
        base = Path('outputs') / 'artifacts' / 'docs'
    else:
        base = Path('outputs') / 'artifacts' / 'misc'
    return base / src.name

def _next_available(p: Path) -> Path:
    if not p.exists():
        return p
    stem, suf = p.stem, p.suffix
    for i in range(1, 10000):
        q = p.with_name(f'{stem}__{i}{suf}')
        if not q.exists():
            return q
    raise RuntimeError(f'No available filename for {p}')

def resolve_collisions(cands: Sequence[Path], dest_of) -> Dict[str, Dict]:
    by_dest: Dict[str, List[Path]] = {}
    for c in cands:
        d = Path(dest_of(c))
        by_dest.setdefault(_norm(d), []).append(c)
    decisions: Dict[str, Dict] = {}
    for d, items in by_dest.items():
        ranked = sorted(items, key=score_path, reverse=True)
        winner = ranked[0]
        losers = ranked[1:]
        decisions[d] = {
            'dest_rel': d,
            'winner': _norm(winner),
            'winner_score': score_path(winner),
            'losers': [_norm(x) for x in losers],
            'loser_scores': { _norm(x): score_path(x) for x in losers },
        }
    return decisions

def transfer(src: Path, dst: Path, mode: str = 'move', overwrite: bool = False) -> Tuple[Path, str]:
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and not overwrite:
        if src.exists() and dst.is_file():
            try:
                if file_hash(src) == file_hash(dst):
                    return dst, 'skip_identical'
            except Exception:
                pass
        dst = _next_available(dst)
        action = 'renamed'
    else:
        action = 'overwrote' if dst.exists() else 'created'
    if mode == 'copy':
        shutil.copy2(src, dst)
    elif mode == 'move':
        try:
            shutil.move(src, dst)
        except shutil.Error:
            shutil.copy2(src, dst)
            try:
                os.remove(src)
            except FileNotFoundError:
                pass
    else:
        raise ValueError('mode must be move or copy')
    return dst, action

def write_report(path: Path, report: Dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() in ('.json', ''):
        if path.suffix == '':
            path = path.with_suffix('.json')
        path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')
    else:
        path.write_text(str(report), encoding='utf-8')
    return path

#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import json
import re

def _root_dir() -> Path:
    return Path(__file__).resolve().parents[1]

def _norm_repo_path(p: str) -> str:
    if not isinstance(p, str):
        return p
    p = p.replace('\\', '/').strip()
    p = re.sub(r'^file:(//)?', '', p)
    p = re.sub(r'^/+Users/.+?/COSMO/', '/', p)  # best-effort: collapse any embedded local absolute
    p = re.sub(r'^/+','/', p)
    if p.startswith('/'):
        return p
    return '/' + p

def _as_rel_under_root(root: Path, repo_path: str) -> Path:
    rp = _norm_repo_path(repo_path).lstrip('/')
    return root / rp

def load_required_deliverables(root: Path) -> list[dict]:
    req = root / 'support' / 'required_deliverables.json'
    if req.exists():
        data = json.loads(req.read_text(encoding='utf-8'))
        if isinstance(data, dict) and 'deliverables' in data:
            data = data['deliverables']
        if isinstance(data, list):
            out = []
            for d in data:
                if isinstance(d, dict) and ('canonical_path' in d or 'canonical' in d):
                    canon = d.get('canonical_path', d.get('canonical'))
                    legacy = d.get('legacy_paths', d.get('legacy', [])) or []
                    if isinstance(legacy, str):
                        legacy = [legacy]
                    out.append({
                        'id': d.get('id') or d.get('name') or Path(str(canon)).name,
                        'name': d.get('name') or d.get('id') or Path(str(canon)).name,
                        'canonical_path': _norm_repo_path(str(canon)),
                        'legacy_paths': [_norm_repo_path(str(x)) for x in legacy if str(x).strip()],
                        'category': d.get('category') or d.get('type') or '',
                        'required': bool(d.get('required', True)),
                        'notes': d.get('notes') or ''
                    })
            return out
    # Fallback: index whatever is already under /outputs (excluding ARTIFACT_INDEX itself)
    outdir = root / 'outputs'
    items = []
    if outdir.exists():
        for p in sorted(outdir.rglob('*')):
            if p.is_file():
                rel = '/' + p.relative_to(root).as_posix()
                if rel == '/outputs/ARTIFACT_INDEX.md':
                    continue
                items.append({'id': p.name, 'name': p.name, 'canonical_path': rel, 'legacy_paths': [], 'category': '', 'required': True, 'notes': 'discovered'})
    return items

def _status(root: Path, canon: str, legacy: list[str]) -> dict:
    cp = _as_rel_under_root(root, canon)
    canon_exists = cp.exists()
    legacy_paths = [(_as_rel_under_root(root, lp), lp) for lp in legacy]
    legacy_exists = [lp for (pp, lp) in legacy_paths if pp.exists()]
    status = 'missing'
    if canon_exists and not legacy_exists:
        status = 'canonical_only'
    elif canon_exists and legacy_exists:
        status = 'migrated_or_duplicated'
    elif (not canon_exists) and legacy_exists:
        status = 'legacy_only'
    return {'status': status, 'canonical_exists': canon_exists, 'legacy_exists': legacy_exists}

def write_index(root: Path, deliverables: list[dict]) -> Path:
    outdir = root / 'outputs'
    outdir.mkdir(parents=True, exist_ok=True)
    idx = outdir / 'ARTIFACT_INDEX.md'
    lines = ['# ARTIFACT_INDEX', '', 'Canonical artifact index for required deliverables.', '']
    lines.append('| Deliverable | Canonical path | Legacy path(s) | Migration status |')
    lines.append('|---|---|---|---|')
    for d in deliverables:
        canon = _norm_repo_path(d['canonical_path'])
        legacy = [_norm_repo_path(x) for x in (d.get('legacy_paths') or [])]
        st = _status(root, canon, legacy)
        legacy_disp = '<br>'.join(legacy) if legacy else ''
        name = d.get('name') or d.get('id') or Path(canon).name
        lines.append(f"| {name} | `{canon}` | {('`'+legacy_disp+'`') if legacy_disp else ''} | {st['status']} |")
    lines += ['', '## Notes', '', '- This file is generated/maintained by `scripts/artifact_discoverability_fix.py`.', '- “Canonical path” refers to paths under `/outputs`.', '']
    idx.write_text('\n'.join(lines), encoding='utf-8')
    return idx

def _collect_path_rewrites(deliverables: list[dict]) -> dict[str, str]:
    m = {}
    for d in deliverables:
        canon = _norm_repo_path(d['canonical_path'])
        for lp in (d.get('legacy_paths') or []):
            lp = _norm_repo_path(lp)
            if lp and canon and lp != canon:
                m[lp] = canon
                m[lp.lstrip('/')] = canon
                m[canon.lstrip('/')] = canon
                m[canon] = canon
    return m

def _rewrite_any_paths(obj, mapping: dict[str, str]):
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = _rewrite_any_paths(v, mapping)
        return obj
    if isinstance(obj, list):
        return [_rewrite_any_paths(x, mapping) for x in obj]
    if isinstance(obj, str):
        s = obj.replace('\\', '/')
        ns = _norm_repo_path(s)
        if ns in mapping:
            return mapping[ns]
        if s in mapping:
            return mapping[s]
        # heuristic: rewrite embedded legacy path segments
        for src, dst in mapping.items():
            if src and src in s:
                return s.replace(src, dst)
        return obj
    return obj

def find_tracker(root: Path) -> Path | None:
    cands = []
    for name in ('PROJECT_TRACKER.json', 'project_tracker.json'):
        p = root / name
        if p.exists():
            return p
    for p in root.glob('*.json'):
        if 'TRACKER' in p.name.upper():
            cands.append(p)
    return sorted(cands)[0] if cands else None

def update_tracker(tracker_path: Path, deliverables: list[dict]) -> bool:
    if not tracker_path or not tracker_path.exists():
        return False
    data = json.loads(tracker_path.read_text(encoding='utf-8'))
    mapping = _collect_path_rewrites(deliverables)
    new_data = _rewrite_any_paths(data, mapping)
    if new_data != data:
        tracker_path.write_text(json.dumps(new_data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        return True
    return True

def main() -> int:
    root = _root_dir()
    deliverables = load_required_deliverables(root)
    write_index(root, deliverables)
    t = find_tracker(root)
    update_tracker(t, deliverables) if t else None
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

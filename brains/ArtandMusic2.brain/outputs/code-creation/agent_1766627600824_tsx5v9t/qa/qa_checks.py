from __future__ import annotations
from pathlib import Path
import argparse, json, hashlib
from datetime import datetime, timezone

def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')

def _sha256(p: Path, limit=2_000_000):
    h=hashlib.sha256()
    with p.open('rb') as f:
        b=f.read(limit)
    h.update(b)
    return h.hexdigest()

def _load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return None

def _remediation_for(check_id: str, catalog: dict|None):
    if isinstance(catalog, dict):
        v=catalog.get(check_id) or {}
        if isinstance(v, dict):
            return v.get('remediation') or v.get('pointer') or v.get('url') or v.get('doc') or v.get('message')
        if isinstance(v, str):
            return v
    return 'See qa/README.md for remediation guidance.'

def _result(check_id, name, status, message='', remediation=''):
    return {'id':check_id,'name':name,'status':status,'message':message,'remediation':remediation}

def check_file_exists(p: Path, check_id: str, name: str, catalog):
    if p.exists() and p.is_file():
        return _result(check_id,name,'PASS',f'Found: {p.as_posix()}',_remediation_for(check_id,catalog))
    return _result(check_id,name,'FAIL',f'Missing required file: {p.as_posix()}',_remediation_for(check_id,catalog))

def check_markdown_sanity(p: Path, catalog):
    if not p.exists():
        return _result('MD_READABLE','Markdown readable','FAIL',f'Cannot read (missing): {p.as_posix()}',_remediation_for('MD_READABLE',catalog))
    try:
        txt=p.read_text(encoding='utf-8')
    except Exception as e:
        return _result('MD_READABLE','Markdown readable','FAIL',f'Cannot read: {e}',_remediation_for('MD_READABLE',catalog))
    if len(txt.strip())<200:
        return _result('MD_MIN_LENGTH','Markdown minimum length','WARN',f'Content very short ({len(txt.strip())} chars).',_remediation_for('MD_MIN_LENGTH',catalog))
    if '# ' not in txt and '## ' not in txt:
        return _result('MD_HAS_HEADINGS','Markdown has headings','WARN','No markdown headings detected (# / ##).',_remediation_for('MD_HAS_HEADINGS',catalog))
    return _result('MD_SANITY','Markdown basic sanity','PASS',f'chars={len(txt)}, sha256={_sha256(p)}',_remediation_for('MD_SANITY',catalog))

def check_required_sections(p: Path, catalog):
    if not p.exists():
        return _result('MD_SECTIONS','Required sections present','FAIL','Draft report missing; cannot validate sections.',_remediation_for('MD_SECTIONS',catalog))
    txt=p.read_text(encoding='utf-8', errors='replace').lower()
    required=['executive summary','methods','results','limitations']
    missing=[s for s in required if s not in txt]
    if missing:
        return _result('MD_SECTIONS','Required sections present','WARN','Missing section keywords: '+', '.join(missing),_remediation_for('MD_SECTIONS',catalog))
    return _result('MD_SECTIONS','Required sections present','PASS','All section keywords found.',_remediation_for('MD_SECTIONS',catalog))

def check_pilot_artifacts(root: Path, globpat: str, catalog):
    paths=[p for p in root.glob(globpat) if p.is_file()]
    if not paths:
        return _result('PILOT_ARTIFACTS','Pilot artifacts present','FAIL',f'No files matched glob: {globpat}',_remediation_for('PILOT_ARTIFACTS',catalog))
    sizes=sum(p.stat().st_size for p in paths)
    ex=', '.join(p.as_posix() for p in paths[:5])
    msg=f'files={len(paths)}, bytes={sizes}; examples: {ex}'
    return _result('PILOT_ARTIFACTS','Pilot artifacts present','PASS',msg,_remediation_for('PILOT_ARTIFACTS',catalog))

def check_catalog_loadable(p: Path, catalog):
    if not p.exists():
        return _result('REMEDIATION_CATALOG','Remediation catalog loadable','WARN',f'Not found: {p.as_posix()}',_remediation_for('REMEDIATION_CATALOG',catalog))
    data=_load_json(p)
    if data is None:
        return _result('REMEDIATION_CATALOG','Remediation catalog loadable','FAIL',f'Invalid JSON: {p.as_posix()}',_remediation_for('REMEDIATION_CATALOG',catalog))
    if not isinstance(data, dict) or not data:
        return _result('REMEDIATION_CATALOG','Remediation catalog loadable','WARN','Catalog JSON is empty or not an object.',_remediation_for('REMEDIATION_CATALOG',catalog))
    return _result('REMEDIATION_CATALOG','Remediation catalog loadable','PASS',f'Loaded {len(data)} entries.',_remediation_for('REMEDIATION_CATALOG',catalog))

def _render_md(report: dict)->str:
    meta=report.get('run',{})
    lines=[]
    lines.append('# QA Report')
    lines.append('')
    lines.append('## Run')
    lines.append(f"- timestamp_utc: {meta.get('timestamp_utc','')}")
    lines.append(f"- root: {meta.get('root','')}")
    lines.append(f"- draft_report: {meta.get('draft_report','')}")
    lines.append(f"- artifacts_glob: {meta.get('artifacts_glob','')}")
    lines.append(f"- status: {meta.get('status','')}")
    lines.append('')
    lines.append('## Checks')
    lines.append('| id | name | status | message | remediation |')
    lines.append('|---|---|---|---|---|')
    for r in report.get('checks',[]):
        def esc(s): return ('' if s is None else str(s)).replace('\n',' ').replace('|','\\|')
        lines.append(f"| {esc(r.get('id'))} | {esc(r.get('name'))} | {esc(r.get('status'))} | {esc(r.get('message'))} | {esc(r.get('remediation'))} |")
    lines.append('')
    summ=report.get('summary',{})
    lines.append('## Summary')
    lines.append(f"- total: {summ.get('total',0)}")
    lines.append(f"- pass: {summ.get('pass',0)}")
    lines.append(f"- warn: {summ.get('warn',0)}")
    lines.append(f"- fail: {summ.get('fail',0)}")
    return '\n'.join(lines)+"\n"

def run_qa(root: Path, draft: Path, artifacts_glob: str, out_json: Path, out_md: Path)->dict:
    root=root.resolve()
    cat_path=root/'qa'/'remediation_catalog.json'
    catalog=_load_json(cat_path) if cat_path.exists() else None
    checks=[]
    checks.append(check_catalog_loadable(cat_path, catalog))
    checks.append(check_file_exists(draft,'DRAFT_EXISTS','Draft report exists',catalog))
    checks.append(check_markdown_sanity(draft,catalog))
    checks.append(check_required_sections(draft,catalog))
    checks.append(check_pilot_artifacts(root, artifacts_glob, catalog))
    counts={'PASS':0,'WARN':0,'FAIL':0}
    for r in checks: counts[r['status']]=counts.get(r['status'],0)+1
    overall='FAIL' if counts.get('FAIL',0)>0 else ('WARN' if counts.get('WARN',0)>0 else 'PASS')
    report={'run':{'timestamp_utc':_now_iso(),'root':root.as_posix(),'draft_report':draft.as_posix(),'artifacts_glob':artifacts_glob,'status':overall},
            'summary':{'total':len(checks),'pass':counts.get('PASS',0),'warn':counts.get('WARN',0),'fail':counts.get('FAIL',0)},
            'checks':checks}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding='utf-8')
    out_md.write_text(_render_md(report), encoding='utf-8')
    return report

def main(argv=None)->int:
    ap=argparse.ArgumentParser(description='Run QA gate and emit QA_REPORT.json / QA_REPORT.md')
    ap.add_argument('--root', default='.', help='Project root (default: current directory)')
    ap.add_argument('--draft', default='DRAFT_REPORT_v0.md', help='Draft report markdown path (relative to root)')
    ap.add_argument('--artifacts-glob', default='pilot_artifacts/**/*', help='Glob under root for pilot artifacts')
    ap.add_argument('--out-json', default='QA_REPORT.json', help='Output JSON report path (relative to root)')
    ap.add_argument('--out-md', default='QA_REPORT.md', help='Output Markdown report path (relative to root)')
    args=ap.parse_args(argv)
    root=Path(args.root)
    draft=(root/args.draft)
    out_json=(root/args.out_json)
    out_md=(root/args.out_md)
    report=run_qa(root, draft, args.artifacts_glob, out_json, out_md)
    return 2 if report.get('run',{}).get('status')=='FAIL' else 0

if __name__=='__main__':
    raise SystemExit(main())

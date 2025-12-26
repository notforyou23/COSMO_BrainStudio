from __future__ import annotations
from pathlib import Path
import json, os, re, time, traceback
from typing import Any, Dict, List, Tuple, Optional

EXIT_OK=0
EXIT_FAIL=2
EXIT_ERROR=3

def _now():
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

def _atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.replace(str(tmp), str(path))

def _append_log(log_path: Optional[Path], msg: str) -> None:
    if not log_path: return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open('a', encoding='utf-8') as f:
        f.write(msg.rstrip('\n') + '\n')

def _load_json(path: Path) -> Tuple[Optional[Any], Optional[str]]:
    try:
        return json.loads(path.read_text(encoding='utf-8')), None
    except Exception as e:
        return None, f'{type(e).__name__}: {e}'

def _simple_validate(schema: Any, data: Any, at: str = '$') -> List[str]:
    errs: List[str] = []
    if not isinstance(schema, dict): return errs
    t = schema.get('type')
    if t:
        m = {'object': dict, 'array': list, 'string': str, 'number': (int, float), 'integer': int, 'boolean': bool, 'null': type(None)}
        py = m.get(t)
        if py and not isinstance(data, py):
            return [f'{at}: expected {t}']
    if t == 'object' and isinstance(data, dict):
        req = schema.get('required') or []
        for k in req:
            if k not in data: errs.append(f'{at}: missing required {k}')
        props = schema.get('properties') or {}
        for k, s in props.items():
            if k in data: errs += _simple_validate(s, data[k], f'{at}.{k}')
    if t == 'array' and isinstance(data, list):
        item_s = schema.get('items')
        if item_s:
            for i, v in enumerate(data):
                errs += _simple_validate(item_s, v, f'{at}[{i}]')
    return errs

def _validate_json_schema(json_path: Path, schema_path: Path) -> Tuple[bool, str]:
    data, e1 = _load_json(json_path)
    if e1: return False, f'Invalid JSON: {e1}'
    schema, e2 = _load_json(schema_path)
    if e2: return False, f'Invalid schema JSON: {e2}'
    try:
        import jsonschema  # type: ignore
        jsonschema.validate(instance=data, schema=schema)
        return True, 'ok'
    except Exception as e:
        errs = _simple_validate(schema, data)
        if errs: return False, '; '.join(errs[:10])
        return False, f'{type(e).__name__}: {e}'

def _check_expected_files(base: Path, expected: List[str]) -> Tuple[bool, List[str]]:
    missing = []
    for rel in expected:
        if not (base / rel).exists():
            missing.append(rel)
    return (len(missing) == 0), missing

def _check_links_markdown(md_path: Path, repo_root: Path) -> Tuple[bool, List[str]]:
    txt = md_path.read_text(encoding='utf-8', errors='replace')
    links = re.findall(r'\[[^\]]*\]\(([^)]+)\)', txt)
    bad: List[str] = []
    for l in links:
        l = l.strip()
        if not l or l.startswith('#') or '://' in l or l.startswith('mailto:'):
            continue
        l = l.split('#', 1)[0]
        if not l: continue
        p = (md_path.parent / l).resolve()
        try:
            p.relative_to(repo_root.resolve())
        except Exception:
            p = (repo_root / l).resolve()
        if not p.exists():
            bad.append(l)
    return (len(bad) == 0), bad

def run_failsafe(repo_root: Path, outputs_dir: Path, qa_dir: Path,
                 config: Optional[Dict[str, Any]] = None, log_path: Optional[Path] = None) -> Tuple[int, Dict[str, Any]]:
    config = config or {}
    report: Dict[str, Any] = {
        'mode': 'failsafe',
        'timestamp_utc': _now(),
        'status': 'error',
        'exit_code': EXIT_ERROR,
        'checks': [],
        'summary': {'passed': 0, 'failed': 0, 'errors': 0},
        'artifacts': {'qa_report': str((qa_dir / 'QA_REPORT.json').as_posix()), 'log': str(log_path.as_posix()) if log_path else None},
        'meta': {'repo_root': str(repo_root), 'outputs_dir': str(outputs_dir), 'qa_dir': str(qa_dir)}
    }
    def add_check(name: str, ok: bool, details: Any = None, severity: str = 'fail'):
        st = 'pass' if ok else ('error' if severity == 'error' else 'fail')
        report['checks'].append({'name': name, 'status': st, 'details': details})
        report['summary']['passed' if ok else ('errors' if st == 'error' else 'failed')] += 1

    try:
        qa_dir.mkdir(parents=True, exist_ok=True)
        if log_path:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text('', encoding='utf-8')
        _append_log(log_path, f'[{_now()}] failsafe QA start')
        add_check('outputs_dir_exists', outputs_dir.exists() and outputs_dir.is_dir(), str(outputs_dir))
        expected = config.get('expected_files')
        if expected is None:
            expected = []
            if outputs_dir.exists() and outputs_dir.is_dir():
                any_files = any(p.is_file() for p in outputs_dir.rglob('*'))
            else:
                any_files = False
            add_check('outputs_nonempty', any_files, 'at least one output file present', severity='fail')
        else:
            ok, missing = _check_expected_files(outputs_dir, list(expected))
            add_check('expected_files_present', ok, {'missing': missing, 'expected': expected})
        for item in config.get('schema_checks', []) or []:
            jp = (outputs_dir / item['path']).resolve()
            sp = (repo_root / item['schema']).resolve()
            ok, msg = (jp.exists() and sp.exists() and _validate_json_schema(jp, sp)[0], None)
            if jp.exists() and sp.exists():
                ok, msg = _validate_json_schema(jp, sp)
            else:
                ok, msg = False, {'json_exists': jp.exists(), 'schema_exists': sp.exists()}
            add_check(f"schema:{item.get('name') or item['path']}", ok, msg)
        if config.get('linkcheck'):
            files = config.get('linkcheck_files') or ['README.md']
            for rel in files:
                mp = (repo_root / rel)
                if not mp.exists():
                    add_check(f'linkcheck:{rel}', False, 'missing markdown', severity='fail')
                    continue
                ok, bad = _check_links_markdown(mp, repo_root)
                add_check(f'linkcheck:{rel}', ok, {'broken': bad})
        status = 'pass' if report['summary']['failed'] == 0 and report['summary']['errors'] == 0 else 'fail'
        report['status'] = status
        report['exit_code'] = EXIT_OK if status == 'pass' else EXIT_FAIL
        _append_log(log_path, f'[{_now()}] failsafe QA done status={status} exit={report["exit_code"]}')
    except Exception:
        report['status'] = 'error'
        report['exit_code'] = EXIT_ERROR
        tb = traceback.format_exc()
        add_check('failsafe_exception', False, tb, severity='error')
        _append_log(log_path, tb)
    finally:
        _atomic_write_json(qa_dir / 'QA_REPORT.json', report)
    return int(report['exit_code']), report

def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', default='.', help='Repository root')
    ap.add_argument('--outputs-dir', default='outputs', help='Outputs directory')
    ap.add_argument('--qa-dir', default='outputs/qa', help='QA directory')
    ap.add_argument('--config', default='', help='Path to JSON config for failsafe checks')
    ap.add_argument('--log', default='', help='Path to log file')
    args = ap.parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    outputs_dir = Path(args.outputs_dir).resolve()
    qa_dir = Path(args.qa_dir).resolve()
    config = None
    if args.config:
        p = Path(args.config).resolve()
        config, err = _load_json(p)
        if err: config = {'schema_checks': [], 'expected_files': [], 'linkcheck': False, '_config_error': err}
    log_path = Path(args.log).resolve() if args.log else (qa_dir / 'QA_LOG.txt')
    code, _ = run_failsafe(repo_root, outputs_dir, qa_dir, config=config, log_path=log_path)
    return code

if __name__ == '__main__':
    raise SystemExit(main())

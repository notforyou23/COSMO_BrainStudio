#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from pathlib import Path
from datetime import datetime, timezone

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()

def _sha256_dir(p: Path) -> str:
    h = hashlib.sha256()
    files = [q for q in p.rglob('*') if q.is_file()]
    files.sort(key=lambda x: str(x).replace(os.sep, '/'))
    for q in files:
        rel = str(q.relative_to(p)).replace(os.sep, '/')
        h.update(rel.encode('utf-8') + b'\0')
        h.update(_sha256_file(q).encode('ascii') + b'\n')
    return h.hexdigest()

def sha256_path(p: Path) -> str | None:
    if not p.exists():
        return None
    if p.is_file():
        return _sha256_file(p)
    if p.is_dir():
        return _sha256_dir(p)
    return None

def norm_rel(p: Path, root: Path) -> str:
    try:
        return str(p.resolve().relative_to(root.resolve())).replace(os.sep, '/')
    except Exception:
        return str(p).replace(os.sep, '/')

def write_index_md(index_path: Path, run: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    ts = run.get('timestamp_utc', '')
    cmd = run.get('command', '')
    inputs = run.get('inputs', [])
    outputs = run.get('outputs', [])
    lines = []
    lines.append(f"## Run {ts}")
    lines.append(f"- Command: `{cmd}`")
    if inputs:
        lines.append("- Inputs:")
        for it in inputs:
            s = it.get('path', '')
            sha = it.get('sha256')
            lines.append(f"  - {s}" + (f" (sha256: {sha})" if sha else ""))
    if outputs:
        lines.append("- Outputs:")
        for it in outputs:
            s = it.get('path', '')
            sha = it.get('sha256')
            lines.append(f"  - {s}" + (f" (sha256: {sha})" if sha else ""))
    block = "\n".join(lines) + "\n\n---\n\n"
    if index_path.exists():
        prev = index_path.read_text(encoding='utf-8')
        if prev and not prev.endswith("\n"):
            prev += "\n"
        index_path.write_text(prev + block, encoding='utf-8')
    else:
        header = "# Outputs ledger\n\nThis file records pipeline runs (timestamp, command, inputs, outputs, sha256).\n\n---\n\n"
        index_path.write_text(header + block, encoding='utf-8')

def update_manifest(manifest_path: Path, run: dict) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"runs": []}
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding='utf-8') or "{}")
        except Exception:
            data = {"runs": []}
    if not isinstance(data, dict):
        data = {"runs": []}
    runs = data.get("runs")
    if not isinstance(runs, list):
        runs = []
        data["runs"] = runs
    runs.append(run)
    manifest_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding='utf-8')

def main() -> int:
    ap = argparse.ArgumentParser(description="Append/update outputs/index.md and optionally outputs/manifest.json with run metadata and sha256 checksums.")
    ap.add_argument('--root', default=str(Path.cwd()), help='Project root (default: cwd)')
    ap.add_argument('--outputs-dir', default='outputs', help='Outputs directory under root (default: outputs)')
    ap.add_argument('--index', default=None, help='Index markdown path (default: <outputs-dir>/index.md)')
    ap.add_argument('--manifest', default=None, help='Manifest json path; if provided or exists, it will be updated (default: <outputs-dir>/manifest.json if --write-manifest)')
    ap.add_argument('--write-manifest', action='store_true', help='Write/update manifest.json in addition to index.md')
    ap.add_argument('--command', default=None, help='Command string to record (default: env RUN_COMMAND or argv)')
    ap.add_argument('--inputs', nargs='*', default=[], help='Declared input paths (relative to root or absolute)')
    ap.add_argument('--produced', nargs='*', default=[], help='Produced artifact paths (relative to root or absolute)')
    ap.add_argument('--key-artifacts', nargs='*', default=['results.json', 'figure.png', 'logs'], help='Key artifacts under outputs-dir to checksum')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_dir = (root / args.outputs_dir).resolve()
    index_path = Path(args.index) if args.index else (out_dir / 'index.md')
    manifest_path = Path(args.manifest) if args.manifest else (out_dir / 'manifest.json')

    ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    cmd = args.command or os.environ.get('RUN_COMMAND') or ' '.join([Path(__file__).name] + list(os.sys.argv[1:]))

    def collect(paths: list[str]) -> list[dict]:
        items = []
        for s in paths:
            p = Path(s)
            p_abs = p if p.is_absolute() else (root / p)
            sha = sha256_path(p_abs)
            items.append({"path": norm_rel(p_abs, root), "sha256": sha})
        return items

    outputs = collect(args.produced)
    for ka in args.key_artifacts:
        p = out_dir / ka
        rec = {"path": norm_rel(p, root), "sha256": sha256_path(p)}
        if rec not in outputs:
            outputs.append(rec)

    run = {
        "timestamp_utc": ts,
        "command": cmd,
        "root": str(root),
        "outputs_dir": norm_rel(out_dir, root),
        "inputs": collect(args.inputs),
        "outputs": outputs,
    }

    write_index_md(index_path, run)
    if args.write_manifest or manifest_path.exists():
        update_manifest(manifest_path, run)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

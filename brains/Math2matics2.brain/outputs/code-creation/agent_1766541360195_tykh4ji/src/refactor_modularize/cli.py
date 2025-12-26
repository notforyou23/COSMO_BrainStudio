"""Command-line interface for the refactor_modularize package.

The CLI provides three subcommands:

- analyze: summarize input artifacts and detect duplicates by content hash
- refactor: produce a deterministic, deduplicated set of artifacts in an output dir
- export: emit a JSON manifest describing the (optionally refactored) artifacts

This module is intentionally lightweight and self-contained so it can be used
even before the rest of the package is imported.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
@dataclass(frozen=True)
class ArtifactInfo:
    path: str
    size: int
    sha256: str

    @property
    def suffix(self) -> str:
        return Path(self.path).suffix.lower()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iter_input_files(inputs: Sequence[str]) -> Iterable[Path]:
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            yield from (q for q in sorted(p.rglob("*")) if q.is_file())
        elif p.is_file():
            yield p
        else:
            raise SystemExit(f"Input not found: {raw}")
def analyze_paths(inputs: Sequence[str]) -> dict:
    infos: list[ArtifactInfo] = []
    by_hash: dict[str, list[str]] = {}
    for p in _iter_input_files(inputs):
        data = p.read_bytes()
        h = _sha256_bytes(data)
        infos.append(ArtifactInfo(path=str(p), size=len(data), sha256=h))
        by_hash.setdefault(h, []).append(str(p))
    dups = {h: ps for h, ps in by_hash.items() if len(ps) > 1}
    return {
        "count": len(infos),
        "total_bytes": sum(i.size for i in infos),
        "duplicates": dups,
        "artifacts": [i.__dict__ for i in infos],
    }


def refactor_to_dir(inputs: Sequence[str], out_dir: str) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    analysis = analyze_paths(inputs)
    written: dict[str, str] = {}
    for a in analysis["artifacts"]:
        p = Path(a["path"])
        h = a["sha256"]
        ext = p.suffix.lower() or ".bin"
        name = f"{h[:12]}{ext}"
        dest = out / name
        if not dest.exists():
            dest.write_bytes(Path(a["path"]).read_bytes())
        written[a["path"]] = str(dest)
    analysis["refactored_dir"] = str(out)
    analysis["refactored_map"] = written
    return analysis
def export_manifest(payload: dict, out_path: str | None) -> str:
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text, encoding="utf-8")
        return out_path
    sys.stdout.write(text)
    return "-"  # stdout


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="refactor-modularize")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("analyze", help="Analyze inputs; detect duplicates by hash.")
    pa.add_argument("inputs", nargs="+", help="Files and/or directories to analyze.")
    pa.add_argument("-o", "--out", help="Write JSON result to this path (default: stdout).")

    pr = sub.add_parser("refactor", help="Deduplicate inputs into an output directory.")
    pr.add_argument("inputs", nargs="+", help="Files and/or directories to refactor.")
    pr.add_argument("--out-dir", required=True, help="Directory to write refactored artifacts.")
    pr.add_argument("-o", "--out", help="Write JSON result/manifest to this path (default: stdout).")

    pe = sub.add_parser("export", help="Export a manifest (optionally after refactor).")
    pe.add_argument("inputs", nargs="+", help="Files and/or directories to include.")
    pe.add_argument("--refactor-out-dir", help="If set, refactor first into this directory.")
    pe.add_argument("-o", "--out", help="Write JSON manifest to this path (default: stdout).")
    return p
def main(argv: Sequence[str] | None = None) -> int:
    ns = _build_parser().parse_args(list(argv) if argv is not None else None)

    if ns.cmd == "analyze":
        payload = analyze_paths(ns.inputs)
        export_manifest(payload, ns.out)
        return 0

    if ns.cmd == "refactor":
        payload = refactor_to_dir(ns.inputs, ns.out_dir)
        export_manifest(payload, ns.out)
        return 0

    if ns.cmd == "export":
        if ns.refactor_out_dir:
            payload = refactor_to_dir(ns.inputs, ns.refactor_out_dir)
        else:
            payload = analyze_paths(ns.inputs)
        export_manifest(payload, ns.out)
        return 0

    raise SystemExit(f"Unknown command: {ns.cmd}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

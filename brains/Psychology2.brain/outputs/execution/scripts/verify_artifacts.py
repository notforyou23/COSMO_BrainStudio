#!/usr/bin/env python3
"""verify_artifacts.py

Verifies required build artifacts and emits runtime/_build/manifest.json.

- Loads config/required_artifacts.json describing required artifact patterns and size rules.
- Fails (nonzero exit) if required artifacts are missing or below minimum size.
- Always writes a manifest containing paths, sizes, hashes, timestamps, and schema versions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


MANIFEST_SCHEMA_VERSION = 1
DEFAULT_CONFIG_REL = Path("config/required_artifacts.json")
DEFAULT_MANIFEST_REL = Path("runtime/_build/manifest.json")


@dataclass
class Rule:
    id: str
    pattern: str
    required: bool = True
    min_size: int = 1
    type: str = "file"  # only 'file' supported for now


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk_size)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _repo_root() -> Path:
    # scripts/verify_artifacts.py -> repo root is parent of scripts
    return Path(__file__).resolve().parents[1]


def _load_config(path: Path) -> Tuple[int, List[Rule]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    schema_version = int(raw.get("schema_version", 1)) if isinstance(raw, dict) else 1

    rules_in: Any
    if isinstance(raw, dict) and "artifacts" in raw:
        rules_in = raw["artifacts"]
    elif isinstance(raw, list):
        rules_in = raw
    else:
        rules_in = []

    rules: List[Rule] = []
    for i, r in enumerate(rules_in or []):
        if not isinstance(r, dict):
            continue
        rid = str(r.get("id") or r.get("name") or f"rule_{i}")
        pattern = str(r.get("pattern") or r.get("path") or r.get("glob") or "")
        if not pattern:
            continue
        required = bool(r.get("required", True))
        min_size = int(r.get("min_size", r.get("min_bytes", 1) or 1))
        rtype = str(r.get("type", "file"))
        rules.append(Rule(id=rid, pattern=pattern, required=required, min_size=min_size, type=rtype))
    return schema_version, rules


def _match_paths(root: Path, pattern: str) -> List[Path]:
    # Support absolute patterns, or treat as relative to repo root.
    p = Path(pattern)
    if p.is_absolute():
        base = p.anchor
        try:
            # Use pathlib glob from the pattern's parent if possible
            parent = p.parent
            pat = p.name
            return sorted([x for x in parent.glob(pat)])
        except Exception:
            return []
    # Use glob relative to root; allow patterns containing subdirs.
    return sorted([x for x in root.glob(pattern)])


def _rel(root: Path, p: Path) -> str:
    try:
        return p.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return p.resolve().as_posix()


def verify_and_manifest(config_path: Path, output_path: Path) -> Tuple[Dict[str, Any], List[str]]:
    root = _repo_root()
    cfg_schema_version = 0
    rules: List[Rule] = []
    errors: List[str] = []

    if not config_path.exists():
        errors.append(f"Missing config: {config_path}")
    else:
        try:
            cfg_schema_version, rules = _load_config(config_path)
        except Exception as e:
            errors.append(f"Failed to load config {config_path}: {e}")

    files: List[Dict[str, Any]] = []
    checks: List[Dict[str, Any]] = []

    seen: set = set()

    for rule in rules:
        matches = _match_paths(root, rule.pattern)
        matched_files: List[str] = []
        rule_errors: List[str] = []

        if rule.required and not matches:
            rule_errors.append(f"Required pattern matched no files: {rule.pattern}")

        for m in matches:
            try:
                if rule.type == "file" and not m.is_file():
                    continue
                st = m.stat()
                size = int(st.st_size)
                if size < int(rule.min_size):
                    rule_errors.append(f"File below min_size ({rule.min_size}): {_rel(root, m)} size={size}")
                entry_key = str(m.resolve())
                if entry_key not in seen:
                    seen.add(entry_key)
                    files.append({
                        "path": _rel(root, m),
                        "size_bytes": size,
                        "sha256": _sha256(m) if m.is_file() else None,
                        "mtime_utc": _iso(st.st_mtime),
                        "ctime_utc": _iso(st.st_ctime),
                    })
                matched_files.append(_rel(root, m))
            except Exception as e:
                rule_errors.append(f"Error processing {_rel(root, m)}: {e}")

        if rule_errors:
            errors.extend([f"[{rule.id}] {msg}" for msg in rule_errors])

        checks.append({
            "id": rule.id,
            "pattern": rule.pattern,
            "required": rule.required,
            "min_size": rule.min_size,
            "type": rule.type,
            "matched": matched_files,
            "ok": len(rule_errors) == 0,
        })

    files_sorted = sorted(files, key=lambda x: x.get("path", ""))
    manifest: Dict[str, Any] = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(root),
        "config_path": str(config_path),
        "config_schema_version": cfg_schema_version,
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
        "environment": {
            "cwd": os.getcwd(),
        },
        "checks": checks,
        "files": files_sorted,
        "summary": {
            "file_count": len(files_sorted),
            "check_count": len(checks),
            "error_count": len(errors),
            "ok": len(errors) == 0,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return manifest, errors


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Verify required artifacts and generate build manifest.")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG_REL), help="Path to required_artifacts.json")
    ap.add_argument("--output", default=str(DEFAULT_MANIFEST_REL), help="Output manifest path")
    args = ap.parse_args(argv)

    root = _repo_root()
    config_path = (root / Path(args.config)).resolve() if not Path(args.config).is_absolute() else Path(args.config).resolve()
    output_path = (root / Path(args.output)).resolve() if not Path(args.output).is_absolute() else Path(args.output).resolve()

    manifest, errors = verify_and_manifest(config_path=config_path, output_path=output_path)

    # Keep console output short and CI-friendly.
    sys.stdout.write(f"MANIFEST_WRITTEN:{_rel(root, output_path)}\n")
    if errors:
        sys.stderr.write("ARTIFACT_VERIFICATION_FAILED\n")
        for e in errors:
            sys.stderr.write(e + "\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

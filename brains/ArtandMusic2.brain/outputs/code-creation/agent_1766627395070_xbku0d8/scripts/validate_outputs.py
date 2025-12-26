from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
def _die(msg: str, code: int = 2) -> None:
    print(f"VALIDATE_OUTPUTS_ERROR: {msg}", file=sys.stderr)
    raise SystemExit(code)


def _as_path(p) -> Path:
    if isinstance(p, str) and p.strip():
        return Path(p)
    _die(f"Invalid path value: {p!r}")


def _resolve_path(p: Path, manifest_path: Path) -> Path:
    if p.is_absolute():
        return p
    repo_root = Path.cwd()
    cands = [repo_root / p, manifest_path.parent / p]
    for c in cands:
        if c.exists():
            return c
    return cands[0]


def _require(cond: bool, msg: str) -> None:
    if not cond:
        _die(msg)
def _load_manifest(manifest_path: Path) -> dict:
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        _die(f"Manifest not found: {manifest_path}")
    if not raw.strip():
        _die(f"Manifest is empty: {manifest_path}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        _die(f"Manifest JSON decode failed ({manifest_path}): {e}")
    _require(isinstance(data, dict), "Manifest must be a JSON object at the top level")
    return data


def _iter_items(obj, key: str):
    val = obj.get(key)
    if val is None:
        return []
    _require(isinstance(val, list), f"Manifest field '{key}' must be a list")
    return val


def _validate_items(items, kind: str, manifest_path: Path) -> int:
    seen_names = set()
    checked = 0
    for i, it in enumerate(items):
        _require(isinstance(it, dict), f"{kind}[{i}] must be an object")
        name = it.get("name") or it.get("id") or it.get("artifact")
        _require(isinstance(name, str) and name.strip(), f"{kind}[{i}].name is required")
        _require(name not in seen_names, f"Duplicate {kind} name: {name}")
        seen_names.add(name)

        p_raw = it.get("path") or it.get("filepath") or it.get("file")
        p = _as_path(p_raw)
        rp = _resolve_path(p, manifest_path)

        if kind == "checklist":
            exists = it.get("exists")
            non_empty = it.get("non_empty") if "non_empty" in it else it.get("nonEmpty")
            if exists is not None:
                _require(bool(exists) is True, f"Checklist item '{name}' reports exists=false")
            if non_empty is not None:
                _require(bool(non_empty) is True, f"Checklist item '{name}' reports non_empty=false")

        _require(rp.exists(), f"Missing file for {kind} item '{name}': {p_raw} -> {rp}")
        _require(rp.is_file(), f"Not a file for {kind} item '{name}': {rp}")
        try:
            size = rp.stat().st_size
        except OSError as e:
            _die(f"Cannot stat file for {kind} item '{name}': {rp} ({e})")
        _require(size > 0, f"Empty file for {kind} item '{name}': {rp}")

        checked += 1
    return checked
def _find_default_manifest() -> Path | None:
    env = os.getenv("QA_RUN_MANIFEST") or os.getenv("RUN_MANIFEST_PATH")
    if env:
        return Path(env)

    repo_root = Path.cwd()
    candidates = [
        repo_root / "run_manifest.json",
        repo_root / "qa_run_manifest.json",
        repo_root / "artifacts" / "run_manifest.json",
        repo_root / ".qa" / "run_manifest.json",
        repo_root / "qa" / "run_manifest.json",
        repo_root / "outputs" / "run_manifest.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate QA run manifest and artifact checklist.")
    ap.add_argument("--manifest", help="Path to normalized run manifest JSON")
    args = ap.parse_args(argv)

    manifest_path = Path(args.manifest) if args.manifest else _find_default_manifest()
    if manifest_path is None:
        _die("No manifest provided and no default manifest found in common locations")

    manifest_path = manifest_path.resolve()
    data = _load_manifest(manifest_path)

    artifacts = _iter_items(data, "artifacts")
    checklist = _iter_items(data, "checklist") or _iter_items(data, "artifact_checklist")

    _require(artifacts or checklist, "Manifest must contain 'artifacts' and/or 'checklist' lists")
    if "schema_version" in data:
        _require(isinstance(data["schema_version"], (int, str)), "schema_version must be int or str")
    if "created_at" in data:
        _require(isinstance(data["created_at"], str) and data["created_at"].strip(), "created_at must be a non-empty string")

    n_art = _validate_items(artifacts, "artifacts", manifest_path) if artifacts else 0
    n_chk = _validate_items(checklist, "checklist", manifest_path) if checklist else 0

    print(f"VALIDATE_OUTPUTS_OK: manifest={manifest_path} artifacts_ok={n_art} checklist_ok={n_chk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

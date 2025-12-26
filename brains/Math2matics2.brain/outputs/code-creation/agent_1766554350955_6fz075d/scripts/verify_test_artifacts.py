from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable, Optional, Tuple
def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _outputs_dir(cli_value: Optional[str]) -> Path:
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    return _repo_root() / "outputs"


def _find_latest_prefix(outputs: Path) -> Tuple[Optional[str], Optional[Path]]:
    # Prefer files that explicitly encode the run result
    candidates: list[Path] = []
    for pat in ("*_exit_code.json", "*_exit_code.txt", "*_exit_code"):
        candidates.extend(outputs.glob(pat))
    candidates = [p for p in candidates if p.is_file()]
    if not candidates:
        # Fallback: any log-like file
        for pat in ("*.log", "*.txt", "*.json"):
            candidates.extend(outputs.glob(pat))
        candidates = [p for p in candidates if p.is_file()]
        if not candidates:
            return None, None

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    name = latest.name
    for marker in ("_exit_code.json", "_exit_code.txt", "_exit_code"):
        if name.endswith(marker):
            return name[: -len(marker)], latest
    # Generic prefix: remove last extension only
    return latest.stem, latest


def _first_existing(outputs: Path, prefix: str, suffixes: Iterable[str]) -> Optional[Path]:
    for s in suffixes:
        p = outputs / f"{prefix}{s}"
        if p.is_file():
            return p
    return None


def _nonempty(p: Path) -> bool:
    try:
        return p.stat().st_size > 0
    except FileNotFoundError:
        return False


def _read_exit_code(p: Path) -> Optional[int]:
    try:
        txt = p.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return None
    if p.suffix.lower() == ".json":
        try:
            data = json.loads(txt) if txt else {}
            if isinstance(data, dict) and "exit_code" in data:
                return int(data["exit_code"])
            if isinstance(data, int):
                return int(data)
        except Exception:
            return None
    # text formats
    for token in (txt, txt.splitlines()[:1][0] if txt.splitlines() else ""):
        token = token.strip()
        if token.lstrip("+-").isdigit():
            try:
                return int(token)
            except Exception:
                pass
    return None
def verify(outputs: Path) -> int:
    outputs = outputs.resolve()
    if not outputs.exists() or not outputs.is_dir():
        print(f"ERROR: outputs dir not found: {outputs}", file=sys.stderr)
        return 2

    prefix, latest_hint = _find_latest_prefix(outputs)
    if not prefix:
        print(f"ERROR: no artifacts found in outputs dir: {outputs}", file=sys.stderr)
        return 2

    # Supported naming variants for run_tests_and_capture_log.py
    stdout_p = _first_existing(outputs, prefix, ("_stdout.log", "_test_stdout.log", "_tests_stdout.log", ".stdout.log", ".log"))
    stderr_p = _first_existing(outputs, prefix, ("_stderr.log", "_test_stderr.log", "_tests_stderr.log", ".stderr.log"))
    exit_p = _first_existing(outputs, prefix, ("_exit_code.json", "_exit_code.txt", "_exit_code"))
    pyver_p = _first_existing(outputs, prefix, ("_python_version.txt", "_python_version.log", "_python.txt", "_python_version"))
    freeze_p = _first_existing(outputs, prefix, ("_pip_freeze.txt", "_pip_freeze.log", "_pip_freeze", "_requirements_freeze.txt"))

    missing = []
    if not stdout_p:
        missing.append("stdout_log")
    if not stderr_p:
        missing.append("stderr_log")
    if not exit_p:
        missing.append("exit_code")
    if not pyver_p:
        missing.append("python_version")
    if not freeze_p:
        missing.append("pip_freeze")

    if missing:
        hint = f" (latest file: {latest_hint.name})" if latest_hint else ""
        print(f"ERROR: missing expected artifacts for prefix '{prefix}' in {outputs}:{hint} -> {', '.join(missing)}", file=sys.stderr)
        return 3

    empty_required = []
    if not _nonempty(stdout_p):
        empty_required.append(stdout_p.name)
    if not _nonempty(exit_p):
        empty_required.append(exit_p.name)
    if not _nonempty(pyver_p):
        empty_required.append(pyver_p.name)
    if not _nonempty(freeze_p):
        empty_required.append(freeze_p.name)

    # stderr is allowed to be empty, but must exist
    if empty_required:
        print(f"ERROR: expected non-empty artifacts are empty: {', '.join(empty_required)}", file=sys.stderr)
        return 4

    exit_code = _read_exit_code(exit_p)
    if exit_code is None:
        print(f"ERROR: could not parse exit code from: {exit_p}", file=sys.stderr)
        return 5

    # Minimal success output (useful for CI logs)
    print(f"OK: verified artifacts for prefix '{prefix}' in {outputs} (exit_code={exit_code})")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verify outputs/ artifacts from the most recent test run are present and non-empty.")
    parser.add_argument("--outputs", default=None, help="Path to outputs/ directory (defaults to repo_root/outputs).")
    args = parser.parse_args(argv)

    # Ensure consistent cwd behavior when run from anywhere
    try:
        os.chdir(_repo_root())
    except Exception:
        pass

    return verify(_outputs_dir(args.outputs))


if __name__ == "__main__":
    raise SystemExit(main())

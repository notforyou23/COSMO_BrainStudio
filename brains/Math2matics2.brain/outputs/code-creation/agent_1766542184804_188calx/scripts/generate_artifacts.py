#!/usr/bin/env python3
"""Generate refactor/modularization artifacts (CLI).

This script is intentionally small and reusable: it relies on
`src.refactor_modularize.utils` for common filesystem/text/json/hashing helpers.
It writes deterministic output paths derived from inputs so runs are reproducible.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    # Shared utilities (created/maintained in the refactor_modularize module).
    from src.refactor_modularize import utils as U  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(
        "Failed to import src.refactor_modularize.utils. "
        "Ensure the project root is on PYTHONPATH.\n"
        f"Import error: {e}"
    )
def _read_prompt(args: argparse.Namespace) -> str:
    if args.prompt_text:
        return args.prompt_text
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8")
    if args.prompt_stdin:
        return sys.stdin.read()
    return ""
def _run_id(args: argparse.Namespace, prompt: str) -> str:
    payload = {
        "mode": args.mode,
        "stage": args.stage,
        "name": args.name,
        "source": str(Path(args.source).resolve()) if args.source else None,
        "prompt_sha256": U.sha256_text(prompt) if prompt else None,
    }
    return U.sha256_text(json.dumps(payload, sort_keys=True))[:16]
def _default_out_dir(base: Optional[str], run_id: str) -> Path:
    # Deterministic: run_id is derived from inputs (no timestamps).
    root = Path(base) if base else ROOT
    return root / "docs" / "artifacts" / run_id
def _export_prompt(prompt: str, out_dir: Path, stem: str) -> Optional[Path]:
    if not prompt.strip():
        return None
    prompts_dir = out_dir.parent.parent / "prompts"
    U.ensure_dir(prompts_dir)
    out_path = prompts_dir / f"{out_dir.name}_{stem}_prompt.txt"
    U.write_text(out_path, prompt)
    return out_path
def generate_artifacts(args: argparse.Namespace) -> Dict[str, Any]:
    prompt = _read_prompt(args)
    run_id = _run_id(args, prompt)
    out_dir = _default_out_dir(args.out_dir or None, run_id)
    U.ensure_dir(out_dir)

    prompt_path = None
    if args.export_prompt:
        prompt_path = _export_prompt(prompt, out_dir, f"{args.name}_{args.stage}")

    manifest: Dict[str, Any] = {
        "run_id": run_id,
        "name": args.name,
        "mode": args.mode,
        "stage": args.stage,
        "cwd": os.getcwd(),
        "source": str(Path(args.source).resolve()) if args.source else None,
        "out_dir": str(out_dir.resolve()),
        "prompt_exported": str(prompt_path) if prompt_path else None,
    }

    # Minimal "artifact" set: manifest + a stable summary text for auditing.
    U.write_json(out_dir / "manifest.json", manifest, indent=2, sort_keys=True)

    summary_lines = [
        f"run_id: {run_id}",
        f"name: {args.name}",
        f"mode: {args.mode}",
        f"stage: {args.stage}",
        f"source: {manifest['source']}",
        f"out_dir: {manifest['out_dir']}",
        f"prompt_exported: {manifest['prompt_exported']}",
    ]
    U.write_text(out_dir / "summary.txt", "\n".join(summary_lines) + "\n")

    # Optional: snapshot the source file/directory listing for traceability.
    if manifest["source"]:
        src = Path(manifest["source"])
        listing = U.list_paths(src) if src.exists() else []
        U.write_json(out_dir / "source_listing.json", listing, indent=2, sort_keys=True)

    return manifest
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--name", default="refactor_modularize", help="Artifact set name.")
    p.add_argument("--mode", default="create", help="Pipeline mode label (metadata only).")
    p.add_argument("--stage", default="stage1_export", help="Stage label (metadata only).")
    p.add_argument("--source", default="", help="Optional source file/dir to list for auditing.")
    p.add_argument("--out-dir", default="", help="Optional base output directory (defaults to project docs/).")

    g = p.add_mutually_exclusive_group()
    g.add_argument("--prompt-text", default="", help="Prompt text to hash/export.")
    g.add_argument("--prompt-file", default="", help="Read prompt text from a file.")
    g.add_argument("--prompt-stdin", action="store_true", help="Read prompt text from stdin.")
    p.add_argument("--export-prompt", action="store_true", help="If set, write the prompt into docs/prompts/.")

    return p
def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    manifest = generate_artifacts(args)
    # Print a stable machine-readable location for downstream scripts.
    print(str(Path(manifest["out_dir"]) / "manifest.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

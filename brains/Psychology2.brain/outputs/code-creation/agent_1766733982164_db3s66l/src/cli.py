"""CLI entrypoint for batch DOI -> open full-text discovery.

Writes run artifacts to ./outputs/ (relative to project root).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from inspect import signature
from pathlib import Path
from typing import Any, Iterable, List, Optional, Tuple
def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _outputs_dir(custom: Optional[str]) -> Path:
    base = Path(custom).expanduser().resolve() if custom else _project_root() / "outputs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _load_text(path: Optional[str]) -> str:
    if not path or path == "-":
        return sys.stdin.read()
    return Path(path).expanduser().read_text(encoding="utf-8", errors="replace")


def _split_dois(text: str) -> List[str]:
    if not text:
        return []
    parts: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "," in line:
            parts.extend([p.strip() for p in line.split(",") if p.strip()])
        else:
            parts.append(line)
    out: List[str] = []
    seen = set()
    for d in parts:
        d = d.strip().strip('"').strip("'")
        if not d or d in seen:
            continue
        seen.add(d)
        out.append(d)
    return out


def _normalize_obj(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return obj.dict()
        except Exception:
            pass
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _normalize_obj(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize_obj(x) for x in obj]
    return {"repr": repr(obj)}
def _call_discovery(dois: List[str], email: Optional[str], max_workers: int, providers: Optional[List[str]], timeout_s: Optional[float]) -> Any:
    try:
        from . import discovery  # type: ignore
    except Exception:  # pragma: no cover
        import discovery  # type: ignore

    candidates = []
    for name in ("discover_dois", "discover", "run_discovery", "run"):
        fn = getattr(discovery, name, None)
        if callable(fn):
            candidates.append((name, fn))
    if not candidates:
        raise SystemExit("No discovery entrypoint found in discovery.py (expected one of: discover_dois, discover, run_discovery, run).")

    name, fn = candidates[0]
    params = signature(fn).parameters
    kwargs = {}
    if "email" in params:
        kwargs["email"] = email
    if "max_workers" in params:
        kwargs["max_workers"] = max_workers
    if "providers" in params and providers is not None:
        kwargs["providers"] = providers
    if "timeout_s" in params and timeout_s is not None:
        kwargs["timeout_s"] = timeout_s
    try:
        return fn(dois, **kwargs)
    except TypeError:
        # fallback to positional-only in some implementations
        return fn(dois)


def _write_artifacts(out_dir: Path, run_id: str, payload: dict) -> Tuple[Path, Path]:
    run_path = out_dir / f"run_{run_id}.json"
    jsonl_path = out_dir / f"run_{run_id}.jsonl"
    run_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    items = payload.get("results") or []
    with jsonl_path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return run_path, jsonl_path
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="doi-discovery", description="Batch DOI discovery for open full-text / primary source access.")
    p.add_argument("--doi", action="append", default=[], help="DOI (repeatable).")
    p.add_argument("--doi-file", default=None, help="Path to file with DOIs (one per line, comma-separated allowed). Use '-' for stdin.")
    p.add_argument("--email", default=None, help="Contact email for Unpaywall (if used).")
    p.add_argument("--providers", default=None, help="Comma-separated provider order override (e.g., unpaywall,openalex,crossref,pmc).")
    p.add_argument("--max-workers", type=int, default=6, help="Max concurrent workers if supported by discovery module.")
    p.add_argument("--timeout-s", type=float, default=None, help="Per-request timeout seconds (if supported).")
    p.add_argument("--outputs-dir", default=None, help="Override outputs directory (default: ./outputs).")
    p.add_argument("--run-id", default=None, help="Override run id (default: utc timestamp).")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    file_dois = _split_dois(_load_text(args.doi_file)) if args.doi_file else []
    cli_dois = []
    for d in args.doi:
        cli_dois.extend(_split_dois(d))
    dois = []
    seen = set()
    for d in (cli_dois + file_dois):
        if d and d not in seen:
            seen.add(d)
            dois.append(d)

    if not dois:
        sys.stderr.write("No DOIs provided. Use --doi or --doi-file (or '-' for stdin).\n")
        return 2

    providers = [p.strip() for p in args.providers.split(",") if p.strip()] if args.providers else None
    out_dir = _outputs_dir(args.outputs_dir)
    run_id = args.run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    t0 = datetime.now(timezone.utc)
    try:
        raw = _call_discovery(dois, args.email, args.max_workers, providers, args.timeout_s)
        ok = True
        err = None
    except Exception as e:
        raw = None
        ok = False
        err = f"{type(e).__name__}: {e}"
    t1 = datetime.now(timezone.utc)

    norm = _normalize_obj(raw)
    # common shapes: list[PerDoiOutcome] or dict with results/logs
    results = norm
    logs = None
    if isinstance(norm, dict):
        results = norm.get("results", norm.get("items", norm.get("outcomes", [])))
        logs = norm.get("logs") or norm.get("events")
    if not isinstance(results, list):
        results = [{"result": results}] if results is not None else []

    payload = {
        "run_id": run_id,
        "created_at": t0.isoformat(),
        "finished_at": t1.isoformat(),
        "duration_s": (t1 - t0).total_seconds(),
        "input": {"dois": dois, "count": len(dois), "providers": providers, "max_workers": args.max_workers, "timeout_s": args.timeout_s},
        "ok": ok,
        "error": err,
        "results": results,
        "logs": logs,
    }

    run_path, jsonl_path = _write_artifacts(out_dir, run_id, payload)
    sys.stdout.write(f"WROTE {run_path.name} and {jsonl_path.name} to {out_dir}\n")
    sys.stdout.write(f"SUMMARY ok={ok} dois={len(dois)} results={len(results)}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

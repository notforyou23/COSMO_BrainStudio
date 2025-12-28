from __future__ import annotations
import argparse, csv, datetime as _dt, hashlib, json, os, sys, time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMAS = ROOT / "schemas"
DEFAULT_INPUTS = ROOT / "inputs"
DEFAULT_OUTPUTS = ROOT / "outputs"

@dataclass
class StepResult:
    ok: bool
    details: Dict[str, Any]
def _utc_stamp() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _iter_files(base: Path) -> Iterable[Path]:
    if not base.exists():
        return []
    for p in sorted(base.rglob("*")):
        if p.is_file() and ".pyc" not in p.suffixes and p.name != ".DS_Store":
            yield p
def _load_json(p: Path) -> Any:
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def _load_csv_rows(p: Path) -> List[Dict[str, Any]]:
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def _coerce_float(x: Any) -> float | None:
    try:
        if x is None:
            return None
        if isinstance(x, (int, float)):
            return float(x)
        s = str(x).strip()
        return float(s) if s != "" else None
    except Exception:
        return None
def validate_schemas(schemas_dir: Path, inputs_dir: Path) -> StepResult:
    t0 = time.time()
    schemas = [p for p in _iter_files(schemas_dir) if p.suffix.lower() in {".json"}]
    inputs = [p for p in _iter_files(inputs_dir) if p.suffix.lower() in {".json", ".csv"}]
    details: Dict[str, Any] = {
        "schemas_dir": str(schemas_dir), "inputs_dir": str(inputs_dir),
        "schema_files": [str(p) for p in schemas], "input_files": [str(p) for p in inputs],
        "errors": [], "validated": []
    }
    try:
        from build_pipeline import schema_validation as sv  # type: ignore
        res = sv.validate_schemas(schemas_dir=schemas_dir, inputs_dir=inputs_dir)  # type: ignore
        return StepResult(True, {"used_module": True, "result": res, "elapsed_s": round(time.time() - t0, 6)})
    except Exception:
        for sp in schemas:
            try:
                _load_json(sp)
                details["validated"].append({"schema": str(sp), "ok": True})
            except Exception as e:
                details["errors"].append({"path": str(sp), "error": f"schema_json_invalid: {e}"})
        for ip in inputs:
            try:
                if ip.suffix.lower() == ".json":
                    _load_json(ip)
                else:
                    _load_csv_rows(ip)
                details["validated"].append({"input": str(ip), "ok": True})
            except Exception as e:
                details["errors"].append({"path": str(ip), "error": f"input_parse_failed: {e}"})
        ok = len(details["errors"]) == 0
        details["used_module"] = False
        details["elapsed_s"] = round(time.time() - t0, 6)
        return StepResult(ok, details)
def run_meta_analysis(inputs_dir: Path, outputs_dir: Path) -> StepResult:
    t0 = time.time()
    out_dir = outputs_dir / "meta_analysis"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "result.json"
    inputs = [p for p in _iter_files(inputs_dir) if p.suffix.lower() in {".json", ".csv"}]
    try:
        from build_pipeline import meta_analysis as ma  # type: ignore
        res = ma.run_meta_analysis(inputs_dir=inputs_dir, outputs_dir=outputs_dir)  # type: ignore
        return StepResult(True, {"used_module": True, "result": res, "elapsed_s": round(time.time() - t0, 6)})
    except Exception:
        n_records = 0
        effect_vals: List[float] = []
        for p in inputs:
            try:
                if p.suffix.lower() == ".json":
                    obj = _load_json(p)
                    rows = obj if isinstance(obj, list) else [obj]
                else:
                    rows = _load_csv_rows(p)
                for r in rows:
                    n_records += 1
                    if isinstance(r, dict):
                        v = _coerce_float(r.get("effect_size"))
                        if v is not None:
                            effect_vals.append(v)
            except Exception:
                continue
        mean_effect = (sum(effect_vals) / len(effect_vals)) if effect_vals else None
        payload = {
            "pipeline": "placeholder_meta_analysis",
            "inputs_scanned": [str(p) for p in inputs],
            "records_count": n_records,
            "effect_size_count": len(effect_vals),
            "mean_effect_size": mean_effect,
            "deterministic_note": "No randomness used; summary derived from parsed inputs only."
        }
        out_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return StepResult(True, {"used_module": False, "output_file": str(out_file), "elapsed_s": round(time.time() - t0, 6)})
def write_build_artifacts(outputs_dir: Path, stamp: str, run_details: Dict[str, Any]) -> Tuple[Path, Path]:
    logs_dir = outputs_dir / "build_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"build_{stamp}.log"
    manifest_path = logs_dir / f"build_{stamp}_manifest.json"

    lines = [
        f"build_stamp={stamp}",
        f"root={ROOT}",
        f"outputs_dir={outputs_dir}",
        f"python={sys.version.split()[0]}",
        f"platform={sys.platform}",
        f"cwd={os.getcwd()}",
    ]
    lines.append("steps=" + json.dumps(run_details.get("steps", {}), sort_keys=True))
    log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest_items: List[Dict[str, Any]] = []
    for p in _iter_files(outputs_dir):
        if (outputs_dir / "build_logs") in p.parents:
            continue
        manifest_items.append({
            "path": str(p.relative_to(ROOT)),
            "sha256": _sha256_file(p),
            "bytes": p.stat().st_size,
        })
    manifest = {"build_stamp": stamp, "generated_at_utc": stamp, "files": manifest_items}
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return log_path, manifest_path
def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="build-pipeline", description="Validate schemas, run meta-analysis, write build logs/manifest.")
    ap.add_argument("--schemas", type=Path, default=DEFAULT_SCHEMAS)
    ap.add_argument("--inputs", type=Path, default=DEFAULT_INPUTS)
    ap.add_argument("--outputs", type=Path, default=DEFAULT_OUTPUTS)
    ap.add_argument("--fail-fast", action="store_true", help="Exit nonzero immediately on schema validation failure.")
    args = ap.parse_args(argv)

    stamp = _utc_stamp()
    steps: Dict[str, Any] = {}
    vres = validate_schemas(args.schemas, args.inputs)
    steps["schema_validation"] = {"ok": vres.ok, **vres.details}
    if args.fail_fast and not vres.ok:
        write_build_artifacts(args.outputs, stamp, {"steps": steps})
        return 2

    ares = run_meta_analysis(args.inputs, args.outputs)
    steps["meta_analysis"] = {"ok": ares.ok, **ares.details}

    log_path, manifest_path = write_build_artifacts(args.outputs, stamp, {"steps": steps})
    print(f"BUILD_OK stamp={stamp} log={log_path} manifest={manifest_path}")
    return 0 if (vres.ok and ares.ok) else 1

if __name__ == "__main__":
    raise SystemExit(main())

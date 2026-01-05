"""Minimal deterministic meta-analysis placeholder.

This module is intentionally small and dependency-free. It consumes already
validated inputs (either in-memory records or file paths), runs a basic fixed-
and random-effects meta-analysis, and writes a compact JSON artifact for build
logging/traceability.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path
import csv
import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union


Number = Union[int, float]


def _to_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if s == "":
        return None
    try:
        return float(s)
    except Exception:
        return None


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_delimited(path: Path, delimiter: str) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def _load_records_from_path(path: Path) -> List[Dict[str, Any]]:
    ext = path.suffix.lower()
    if ext == ".json":
        obj = _read_json(path)
        if isinstance(obj, list):
            return [r for r in obj if isinstance(r, dict)]
        if isinstance(obj, dict):
            for k in ("studies", "records", "data", "rows"):
                v = obj.get(k)
                if isinstance(v, list):
                    return [r for r in v if isinstance(r, dict)]
            return [obj]
        return []
    if ext in (".csv", ".tsv"):
        return _read_delimited(path, delimiter="\t" if ext == ".tsv" else ",")
    raise ValueError(f"Unsupported input format: {path.name}")


def _extract_effect_se(rec: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    yi = _to_float(rec.get("effect_size"))
    if yi is None:
        yi = _to_float(rec.get("effect"))
    if yi is None:
        yi = _to_float(rec.get("yi"))
    if yi is None:
        return None

    se = _to_float(rec.get("se"))
    if se is None:
        var = _to_float(rec.get("variance"))
        if var is None:
            var = _to_float(rec.get("var"))
        if var is not None and var >= 0:
            se = sqrt(var)
    if se is None or se <= 0:
        return None
    return yi, se


@dataclass(frozen=True)
class MetaAnalysisResult:
    k: int
    fixed_effect: float
    fixed_se: float
    fixed_ci95: Tuple[float, float]
    q: Optional[float]
    i2: Optional[float]
    tau2_dl: Optional[float]
    random_effect: Optional[float]
    random_se: Optional[float]
    random_ci95: Optional[Tuple[float, float]]


def _ci95(mean: float, se: float) -> Tuple[float, float]:
    z = 1.959963984540054
    return (mean - z * se, mean + z * se)


def _meta_analyze(effects: Sequence[Tuple[float, float]]) -> MetaAnalysisResult:
    ys = [y for y, _ in effects]
    ses = [se for _, se in effects]
    ws = [1.0 / (se * se) for se in ses]
    sw = sum(ws)
    fe = sum(w * y for w, y in zip(ws, ys)) / sw
    fe_se = sqrt(1.0 / sw)
    fe_ci = _ci95(fe, fe_se)

    q = None
    i2 = None
    tau2 = None
    re = None
    re_se = None
    re_ci = None

    k = len(effects)
    if k >= 2:
        q = sum(w * (y - fe) ** 2 for w, y in zip(ws, ys))
        c = sw - (sum(w * w for w in ws) / sw)
        tau2 = max(0.0, (q - (k - 1)) / c) if c > 0 else 0.0
        denom = q if q and q > 0 else None
        if denom:
            i2 = max(0.0, (q - (k - 1)) / q)
        wre = [1.0 / (se * se + tau2) for se in ses]
        swre = sum(wre)
        re = sum(w * y for w, y in zip(wre, ys)) / swre
        re_se = sqrt(1.0 / swre)
        re_ci = _ci95(re, re_se)

    return MetaAnalysisResult(
        k=k,
        fixed_effect=fe,
        fixed_se=fe_se,
        fixed_ci95=fe_ci,
        q=q,
        i2=i2,
        tau2_dl=tau2,
        random_effect=re,
        random_se=re_se,
        random_ci95=re_ci,
    )


def run_meta_analysis(
    validated_inputs: Any,
    outputs_dir: Union[str, Path],
    *,
    output_filename: str = "meta_analysis_results.json",
) -> Dict[str, Any]:
    """Run a minimal meta-analysis and write a JSON artifact.

    Parameters
    ----------
    validated_inputs:
        One of:
        - list[dict]: in-memory study records
        - dict with key 'records'/'studies' containing list[dict]
        - dict with key 'validated_files'/'files' containing list[str|Path]
        - list[str|Path]: file paths
    outputs_dir:
        Directory where the JSON artifact will be written.

    Returns
    -------
    dict with keys: 'result', 'artifact_path', 'records_used'
    """
    out_dir = Path(outputs_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths: List[Path] = []
    records: List[Dict[str, Any]] = []

    if isinstance(validated_inputs, list):
        if all(isinstance(x, dict) for x in validated_inputs):
            records = list(validated_inputs)
        else:
            paths = [Path(x) for x in validated_inputs]
    elif isinstance(validated_inputs, dict):
        for k in ("records", "studies", "data", "rows"):
            v = validated_inputs.get(k)
            if isinstance(v, list) and all(isinstance(x, dict) for x in v):
                records = list(v)
                break
        if not records:
            for k in ("validated_files", "files", "paths"):
                v = validated_inputs.get(k)
                if isinstance(v, list):
                    paths = [Path(x) for x in v]
                    break
    else:
        raise TypeError("validated_inputs must be a list or dict")

    for p in paths:
        p = p if p.is_absolute() else (Path.cwd() / p)
        records.extend(_load_records_from_path(p))

    effects: List[Tuple[float, float]] = []
    cleaned: List[Dict[str, Any]] = []
    for rec in records:
        ex = _extract_effect_se(rec)
        if not ex:
            continue
        yi, se = ex
        cleaned.append({"effect": yi, "se": se})
        effects.append((yi, se))

    if not effects:
        raise ValueError("No usable study records found (need effect + se or variance).")

    result = _meta_analyze(effects)
    artifact = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "result": asdict(result),
        "records_used": len(cleaned),
        "inputs_summary": {"total_records_seen": len(records)},
        "study_effects": cleaned,
    }

    artifact_path = out_dir / output_filename
    artifact_path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"result": asdict(result), "artifact_path": str(artifact_path), "records_used": len(cleaned)}

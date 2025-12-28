from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _slugify(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"_+", "_", s).strip("_") or "gate"


def _find_project_root(start: Optional[Path] = None) -> Path:
    start = (start or Path(__file__)).resolve()
    for p in (start if start.is_dir() else start.parent).parents:
        if p.name == "src":
            return p.parent
    # Fallback: assume file is under <root>/src/utils/
    return start.parents[2]


def get_logs_dir(project_root: Optional[Path] = None) -> Path:
    root = project_root or _find_project_root()
    d = root / "outputs" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class GateResult:
    check: str
    passed: bool
    metrics: Dict[str, Any] = field(default_factory=dict)
    message: str = ""
    timestamp_utc: str = field(default_factory=_utc_now_iso)

    @property
    def status(self) -> str:
        return "pass" if self.passed else "fail"


def write_gate_result(
    result: GateResult,
    *,
    run_id: Optional[str] = None,
    logs_dir: Optional[Path] = None,
    also_append_jsonl: bool = True,
) -> Path:
    logs_dir = logs_dir or get_logs_dir()
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(result.check)

    payload: Dict[str, Any] = asdict(result)
    payload["run_id"] = run_id

    out_path = logs_dir / f"{run_id}__{slug}.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if also_append_jsonl:
        jsonl_path = logs_dir / f"{run_id}__gate_results.jsonl"
        with jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, sort_keys=True) + "\n")

    return out_path


def write_gate_summary(
    *,
    gate_name: str,
    passed: bool,
    check_results: Dict[str, GateResult],
    run_id: Optional[str] = None,
    logs_dir: Optional[Path] = None,
) -> Path:
    logs_dir = logs_dir or get_logs_dir()
    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload: Dict[str, Any] = {
        "gate": gate_name,
        "status": "pass" if passed else "fail",
        "passed": bool(passed),
        "run_id": run_id,
        "timestamp_utc": _utc_now_iso(),
        "checks": {k: asdict(v) for k, v in check_results.items()},
    }
    out_path = logs_dir / f"{run_id}__{_slugify(gate_name)}__summary.json"
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path


def gate_result_from_counts(
    *,
    check: str,
    violation_counts: Dict[str, int],
    message: str = "",
    extra_metrics: Optional[Dict[str, Any]] = None,
) -> GateResult:
    counts = {k: int(v) for k, v in (violation_counts or {}).items()}
    total = sum(counts.values())
    metrics: Dict[str, Any] = {"violations_total": total, **counts}
    if extra_metrics:
        metrics.update(extra_metrics)
    return GateResult(check=check, passed=(total == 0), metrics=metrics, message=message)

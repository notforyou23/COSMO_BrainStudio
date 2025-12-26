from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import hashlib
from typing import Any, Dict, Iterable, Optional


@dataclass(frozen=True)
class PipelineResult:
    output_dir: Path
    artifacts: Dict[str, Path]
    report: Dict[str, Any]


def _stable_digest(items: Iterable[str]) -> str:
    h = hashlib.sha256()
    for s in items:
        h.update(s.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(path)


def _atomic_write_json(path: Path, obj: Any) -> None:
    text = json.dumps(obj, indent=2, sort_keys=True) + "\n"
    _atomic_write_text(path, text, encoding="utf-8")


def run_pipeline(
    output_dir: Optional[Path] = None,
    *,
    run_id: str = "minipipe-stage1",
) -> PipelineResult:
    """Deterministically create an outputs directory with a small set of artifacts.

    Artifacts:
      - outputs/report.json: JSON report with stable keys and values
      - outputs/metrics.json: small metrics payload
      - outputs/summary.txt: human-readable summary
    """
    base = Path(output_dir) if output_dir is not None else Path("outputs")
    base = base.resolve()
    base.mkdir(parents=True, exist_ok=True)

    inputs = [
        "alpha",
        "bravo",
        "charlie",
    ]
    digest = _stable_digest(inputs)

    metrics = {
        "n_items": len(inputs),
        "digest_sha256": digest,
        "score": round(len(digest) / 100.0, 4),
    }

    report: Dict[str, Any] = {
        "run_id": run_id,
        "status": "success",
        "artifacts": {
            "report_json": "report.json",
            "metrics_json": "metrics.json",
            "summary_txt": "summary.txt",
        },
        "inputs": inputs,
        "metrics": metrics,
        "schema": {
            "required_keys": ["run_id", "status", "artifacts", "inputs", "metrics", "schema"],
            "version": 1,
        },
    }

    report_path = base / "report.json"
    metrics_path = base / "metrics.json"
    summary_path = base / "summary.txt"

    _atomic_write_json(metrics_path, metrics)
    _atomic_write_json(report_path, report)

    summary = (
        f"minipipe pipeline report\n"
        f"run_id: {run_id}\n"
        f"status: success\n"
        f"n_items: {metrics['n_items']}\n"
        f"digest_sha256: {metrics['digest_sha256']}\n"
    )
    _atomic_write_text(summary_path, summary)

    artifacts = {
        "report.json": report_path,
        "metrics.json": metrics_path,
        "summary.txt": summary_path,
    }
    return PipelineResult(output_dir=base, artifacts=artifacts, report=report)

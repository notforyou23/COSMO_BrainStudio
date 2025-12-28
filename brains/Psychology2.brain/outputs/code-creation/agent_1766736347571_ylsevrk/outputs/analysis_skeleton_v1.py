"""Minimal, runnable analysis skeleton for a meta-analysis project.

- Loads extracted study data from outputs/data_extraction_template_v1.csv if present.
- Otherwise uses an in-memory placeholder dataset.
- Computes a small summary and writes at least one output file to outputs/.
"""

from __future__ import annotations

from pathlib import Path
import json
import math
import csv
from typing import Dict, Any, List, Tuple


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = Path(__file__).resolve().parent
EXTRACTION_CSV = OUTPUTS_DIR / "data_extraction_template_v1.csv"
SUMMARY_CSV = OUTPUTS_DIR / "analysis_summary_v1.csv"
SUMMARY_JSON = OUTPUTS_DIR / "analysis_summary_v1.json"


REQUIRED_COLUMNS = [
    "study_id",
    "effect_size",
    "standard_error",
    "outcome",
    "group",
    "notes",
]


def _read_csv(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return (reader.fieldnames or []), rows


def _to_float(x: Any) -> float | None:
    if x is None:
        return None
    s = str(x).strip()
    if s == "" or s.lower() in {"na", "nan", "none", "null"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _placeholder_rows() -> List[Dict[str, Any]]:
    return [
        {
            "study_id": "S1",
            "effect_size": 0.20,
            "standard_error": 0.10,
            "outcome": "primary",
            "group": "overall",
            "notes": "placeholder",
        },
        {
            "study_id": "S2",
            "effect_size": 0.05,
            "standard_error": 0.12,
            "outcome": "primary",
            "group": "overall",
            "notes": "placeholder",
        },
        {
            "study_id": "S3",
            "effect_size": -0.10,
            "standard_error": 0.08,
            "outcome": "primary",
            "group": "overall",
            "notes": "placeholder",
        },
    ]


def load_extraction_data() -> List[Dict[str, Any]]:
    if EXTRACTION_CSV.exists():
        header, rows = _read_csv(EXTRACTION_CSV)
        missing = [c for c in REQUIRED_COLUMNS if c not in set(header)]
        if missing:
            raise ValueError(
                f"Extraction file missing required columns: {missing}. "
                f"Found columns: {header}"
            )
        parsed: List[Dict[str, Any]] = []
        for r in rows:
            parsed.append(
                {
                    "study_id": (r.get("study_id") or "").strip(),
                    "effect_size": _to_float(r.get("effect_size")),
                    "standard_error": _to_float(r.get("standard_error")),
                    "outcome": (r.get("outcome") or "").strip(),
                    "group": (r.get("group") or "").strip(),
                    "notes": (r.get("notes") or "").strip(),
                }
            )
        parsed = [r for r in parsed if r.get("study_id")]
        if not parsed:
            return _placeholder_rows()
        return parsed
    return _placeholder_rows()


def fixed_effect_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    clean = [
        r
        for r in rows
        if r.get("effect_size") is not None
        and r.get("standard_error") is not None
        and r.get("standard_error") > 0
    ]
    k = len(clean)
    if k == 0:
        return {
            "k": 0,
            "mean_effect": None,
            "se_mean": None,
            "ci95_low": None,
            "ci95_high": None,
        }

    weights = [1.0 / (r["standard_error"] ** 2) for r in clean]  # type: ignore[index]
    sum_w = sum(weights)
    mean = sum(w * r["effect_size"] for w, r in zip(weights, clean)) / sum_w  # type: ignore[index]
    se_mean = math.sqrt(1.0 / sum_w)
    z = 1.96
    return {
        "k": k,
        "mean_effect": mean,
        "se_mean": se_mean,
        "ci95_low": mean - z * se_mean,
        "ci95_high": mean + z * se_mean,
    }


def write_summary_csv(summary: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["k", "mean_effect", "se_mean", "ci95_low", "ci95_high"],
        )
        writer.writeheader()
        writer.writerow(summary)


def main() -> int:
    rows = load_extraction_data()
    summary = fixed_effect_summary(rows)
    write_summary_csv(summary, SUMMARY_CSV)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE:{SUMMARY_CSV.relative_to(BASE_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

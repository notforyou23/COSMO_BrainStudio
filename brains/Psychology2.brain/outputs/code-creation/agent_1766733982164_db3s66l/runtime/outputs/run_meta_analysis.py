#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import math
import csv

ROOT = Path(__file__).resolve().parents[0]
BUILD_DIR = ROOT / "_build"

DEFAULT_INPUT = ROOT / "extracted_effects.csv"
TEMPLATE_INPUT = ROOT / "extraction_template_effects.csv"
TOY_INPUT = ROOT / "toy_effects.csv"

REQUIRED_COLS = ["study_id", "effect", "se"]


def ensure_build_dir() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)


def write_template(path: Path) -> None:
    rows = [
        {"study_id": "StudyA", "effect": "0.20", "se": "0.10", "notes": "example (generic effect size)"},
        {"study_id": "StudyB", "effect": "0.05", "se": "0.12", "notes": "example"},
        {"study_id": "StudyC", "effect": "0.35", "se": "0.15", "notes": "example"},
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def read_effects_csv(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if not r.fieldnames:
            raise ValueError(f"Empty CSV: {path}")
        cols = [c.strip() for c in r.fieldnames]
        missing = [c for c in REQUIRED_COLS if c not in cols]
        if missing:
            raise ValueError(f"Missing required columns {missing} in {path}. Expected at least {REQUIRED_COLS}.")
        out = []
        for i, row in enumerate(r, start=2):
            try:
                sid = str(row.get("study_id", "")).strip()
                if not sid:
                    sid = f"row_{i}"
                yi = float(str(row["effect"]).strip())
                sei = float(str(row["se"]).strip())
                if not (sei > 0 and math.isfinite(sei) and math.isfinite(yi)):
                    raise ValueError("Non-finite values or se<=0")
                out.append({"study_id": sid, "effect": yi, "se": sei})
            except Exception as e:
                raise ValueError(f"Bad row at line {i} in {path}: {e}") from e
    if len(out) < 2:
        raise ValueError(f"Need at least 2 studies to pool; found {len(out)} in {path}")
    return out


def fixed_effect_meta(studies: list[dict]) -> dict:
    ws = []
    for s in studies:
        v = s["se"] ** 2
        ws.append(1.0 / v)
    sumw = sum(ws)
    yhat = sum(w * s["effect"] for w, s in zip(ws, studies)) / sumw
    se = math.sqrt(1.0 / sumw)
    ci_lo, ci_hi = yhat - 1.96 * se, yhat + 1.96 * se
    q = sum(w * (s["effect"] - yhat) ** 2 for w, s in zip(ws, studies))
    df = len(studies) - 1
    return {
        "model": "fixed",
        "k": len(studies),
        "estimate": yhat,
        "se": se,
        "ci_low_95": ci_lo,
        "ci_high_95": ci_hi,
        "Q": q,
        "df": df,
    }


def dersimonian_laird_tau2(studies: list[dict], y_fixed: float) -> float:
    ws = [1.0 / (s["se"] ** 2) for s in studies]
    q = sum(w * (s["effect"] - y_fixed) ** 2 for w, s in zip(ws, studies))
    df = len(studies) - 1
    sumw = sum(ws)
    sumw2 = sum(w * w for w in ws)
    c = sumw - (sumw2 / sumw) if sumw > 0 else 0.0
    tau2 = max(0.0, (q - df) / c) if c > 0 else 0.0
    return tau2


def random_effects_meta(studies: list[dict]) -> dict:
    fe = fixed_effect_meta(studies)
    tau2 = dersimonian_laird_tau2(studies, fe["estimate"])
    ws = [1.0 / (s["se"] ** 2 + tau2) for s in studies]
    sumw = sum(ws)
    yhat = sum(w * s["effect"] for w, s in zip(ws, studies)) / sumw
    se = math.sqrt(1.0 / sumw)
    ci_lo, ci_hi = yhat - 1.96 * se, yhat + 1.96 * se
    i2 = max(0.0, (fe["Q"] - fe["df"]) / fe["Q"]) * 100.0 if fe["Q"] > 0 else 0.0
    return {
        "model": "random_DL",
        "k": len(studies),
        "estimate": yhat,
        "se": se,
        "ci_low_95": ci_lo,
        "ci_high_95": ci_hi,
        "tau2_DL": tau2,
        "I2_percent": i2,
        "Q": fe["Q"],
        "df": fe["df"],
    }


def write_summary_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = []
    for r in rows:
        for k in r.keys():
            if k not in fieldnames:
                fieldnames.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    ap = argparse.ArgumentParser(description="Minimal meta-analysis starter: pool generic effect size + SE from CSV.")
    ap.add_argument("--input", type=str, default=str(DEFAULT_INPUT),
                    help=f"CSV with columns {REQUIRED_COLS} (default: {DEFAULT_INPUT.name})")
    ap.add_argument("--make-template", action="store_true", help="Write an extraction template CSV and exit.")
    args = ap.parse_args()

    if args.make_template:
        write_template(TEMPLATE_INPUT)
        write_template(TOY_INPUT)
        print(f"WROTE_TEMPLATE:{TEMPLATE_INPUT}")
        print(f"WROTE_TOY:{TOY_INPUT}")
        return 0

    ensure_build_dir()

    in_path = Path(args.input)
    if not in_path.is_absolute():
        in_path = ROOT / in_path

    if not in_path.exists():
        write_template(in_path)
        studies = read_effects_csv(in_path)
    else:
        studies = read_effects_csv(in_path)

    fe = fixed_effect_meta(studies)
    re = random_effects_meta(studies)
    out_summary = BUILD_DIR / "meta_summary.csv"
    write_summary_csv(out_summary, [fe, re])

    out_studies = BUILD_DIR / "study_data_clean.csv"
    with out_studies.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["study_id", "effect", "se", "var", "weight_FE"])
        w.writeheader()
        for s in studies:
            var = s["se"] ** 2
            w.writerow({"study_id": s["study_id"], "effect": s["effect"], "se": s["se"], "var": var, "weight_FE": 1.0 / var})

    print(f"INPUT_USED:{in_path}")
    print(f"OUTPUT_SUMMARY:{out_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

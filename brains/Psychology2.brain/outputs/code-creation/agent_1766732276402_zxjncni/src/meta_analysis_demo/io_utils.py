from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

import json


@dataclass(frozen=True)
class CanonicalPaths:
    root: Path
    outputs: Path
    tables: Path
    figures: Path
    build: Path
    logs: Path
    intermediate: Path


DEFAULT_SCHEMA = {
    "study": ("study", "study_id", "study_name", "label", "author_year", "author", "trial"),
    "yi": ("yi", "effect", "es", "log_rr", "log_or", "md", "smd"),
    "sei": ("sei", "se", "std_error", "stderr", "standard_error"),
}


def ensure_canonical_dirs(root: Path) -> CanonicalPaths:
    root = Path(root)
    outputs = root / "outputs"
    tables = outputs / "tables"
    figures = outputs / "figures"
    build = root / "_build"
    logs = build / "logs"
    intermediate = build / "intermediate"
    for p in (outputs, tables, figures, build, logs, intermediate):
        p.mkdir(parents=True, exist_ok=True)
    return CanonicalPaths(root, outputs, tables, figures, build, logs, intermediate)


def _lower_map(cols: Iterable[str]) -> Dict[str, str]:
    return {str(c).strip().lower(): str(c) for c in cols}


def _resolve_column(col_map: Mapping[str, str], aliases: Iterable[str]) -> Optional[str]:
    for a in aliases:
        key = str(a).strip().lower()
        if key in col_map:
            return col_map[key]
    return None


def read_toy_csv(csv_path: Path) -> "Any":
    csv_path = Path(csv_path)
    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError("pandas is required to read the toy CSV") from e
    if not csv_path.exists():
        raise FileNotFoundError(str(csv_path))
    df = pd.read_csv(csv_path)
    if df.shape[0] == 0:
        raise ValueError(f"Input CSV has 0 rows: {csv_path}")
    return df


def validate_and_standardize_effects_df(
    df: "Any",
    schema: Mapping[str, Tuple[str, ...]] = DEFAULT_SCHEMA,
) -> "Any":
    try:
        import pandas as pd  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ImportError("pandas is required for schema validation") from e
    if df is None or getattr(df, "shape", (0, 0))[0] == 0:
        raise ValueError("Empty dataframe provided")
    col_map = _lower_map(df.columns)
    resolved: Dict[str, str] = {}
    for canonical, aliases in schema.items():
        src = _resolve_column(col_map, aliases)
        if not src:
            raise ValueError(f"Missing required column for '{canonical}'. Accepted: {list(aliases)}")
        resolved[canonical] = src

    out = df.rename(columns={resolved["study"]: "study", resolved["yi"]: "yi", resolved["sei"]: "sei"}).copy()
    out["study"] = out["study"].astype(str)
    out["yi"] = pd.to_numeric(out["yi"], errors="coerce")
    out["sei"] = pd.to_numeric(out["sei"], errors="coerce")
    bad = out["yi"].isna() | out["sei"].isna() | (out["sei"] <= 0)
    if bad.any():
        idx = out.index[bad].tolist()[:10]
        raise ValueError(f"Invalid yi/sei values (nan or sei<=0) in rows (first up to 10): {idx}")
    return out[["study", "yi", "sei"]]


def write_csv_table(df: "Any", out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_csv(out_path, index=False)
    except Exception:
        import pandas as pd  # type: ignore
        pd.DataFrame(df).to_csv(out_path, index=False)
    return out_path


def write_json(obj: Any, out_path: Path, *, indent: int = 2) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(obj, indent=indent, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return out_path


def write_text(text: str, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text if text.endswith("\n") else (text + "\n"), encoding="utf-8")
    return out_path


def write_run_manifest(
    paths: CanonicalPaths,
    *,
    input_csv: Optional[Path] = None,
    outputs: Optional[Mapping[str, str]] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> Path:
    manifest = {
        "input_csv": str(input_csv) if input_csv else None,
        "outputs": dict(outputs) if outputs else {},
        "metadata": dict(metadata) if metadata else {},
    }
    return write_json(manifest, paths.build / "manifest.json")

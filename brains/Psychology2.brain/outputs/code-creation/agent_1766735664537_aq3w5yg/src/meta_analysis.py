from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, Optional, Sequence, Tuple, Dict, Any
import math
import pandas as pd
import numpy as np


REQUIRED_COLS_DEFAULT = ("effect", "se")


@dataclass(frozen=True)
class MetaResult:
    table: pd.DataFrame
    details: Dict[str, Any]


def read_extraction_csv(path: str | "os.PathLike[str]") -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    return df


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _z_pvalue(z: float) -> float:
    return 2.0 * (1.0 - _norm_cdf(abs(z)))


def _ensure_effect_inputs(df: pd.DataFrame, effect_col: str, se_col: str, var_col: Optional[str]) -> Tuple[np.ndarray, np.ndarray]:
    if effect_col not in df.columns:
        raise ValueError(f"Missing effect column: {effect_col}")
    yi = pd.to_numeric(df[effect_col], errors="coerce").to_numpy()
    if se_col in df.columns:
        sei = pd.to_numeric(df[se_col], errors="coerce").to_numpy()
    elif var_col and var_col in df.columns:
        vi = pd.to_numeric(df[var_col], errors="coerce").to_numpy()
        sei = np.sqrt(vi)
    else:
        raise ValueError(f"Missing SE/VAR columns: need '{se_col}' or '{var_col}'")
    m = np.isfinite(yi) & np.isfinite(sei) & (sei > 0)
    return yi[m], sei[m]


def _pool_fixed(yi: np.ndarray, sei: np.ndarray) -> Dict[str, float]:
    wi = 1.0 / (sei ** 2)
    mu = float(np.sum(wi * yi) / np.sum(wi))
    se = float(math.sqrt(1.0 / np.sum(wi)))
    z = mu / se if se > 0 else float("nan")
    p = _z_pvalue(z) if np.isfinite(z) else float("nan")
    return {"k": int(len(yi)), "estimate": mu, "se": se, "ci_low": mu - 1.96 * se, "ci_high": mu + 1.96 * se, "z": z, "p": p}


def _tau2_dl(yi: np.ndarray, sei: np.ndarray) -> Tuple[float, float, float]:
    wi = 1.0 / (sei ** 2)
    mu = np.sum(wi * yi) / np.sum(wi)
    q = float(np.sum(wi * (yi - mu) ** 2))
    k = len(yi)
    c = float(np.sum(wi) - (np.sum(wi ** 2) / np.sum(wi)))
    tau2 = max(0.0, (q - (k - 1)) / c) if (k > 1 and c > 0) else 0.0
    i2 = max(0.0, (q - (k - 1)) / q) if (k > 1 and q > 0) else 0.0
    return tau2, q, i2


def _pool_random_dl(yi: np.ndarray, sei: np.ndarray) -> Dict[str, float]:
    tau2, q, i2 = _tau2_dl(yi, sei)
    wi = 1.0 / (sei ** 2 + tau2)
    mu = float(np.sum(wi * yi) / np.sum(wi))
    se = float(math.sqrt(1.0 / np.sum(wi))) if np.sum(wi) > 0 else float("nan")
    z = mu / se if se and se > 0 else float("nan")
    p = _z_pvalue(z) if np.isfinite(z) else float("nan")
    return {
        "k": int(len(yi)),
        "estimate": mu,
        "se": se,
        "ci_low": mu - 1.96 * se if np.isfinite(se) else float("nan"),
        "ci_high": mu + 1.96 * se if np.isfinite(se) else float("nan"),
        "z": z,
        "p": p,
        "tau2": float(tau2),
        "Q": float(q),
        "I2": float(i2),
    }


def meta_analyze(
    df: pd.DataFrame,
    *,
    effect_col: str = "effect",
    se_col: str = "se",
    var_col: Optional[str] = "var",
    group_cols: Optional[Sequence[str]] = None,
) -> MetaResult:
    group_cols = list(group_cols) if group_cols else []
    rows = []
    details: Dict[str, Any] = {"effect_col": effect_col, "se_col": se_col, "var_col": var_col, "group_cols": group_cols}
    if group_cols:
        grouped = df.groupby(group_cols, dropna=False, sort=False)
        items = list(grouped)
    else:
        items = [((), df)]
    for key, sub in items:
        yi, sei = _ensure_effect_inputs(sub, effect_col, se_col, var_col)
        label = key if isinstance(key, tuple) else (key,)
        fixed = _pool_fixed(yi, sei)
        random = _pool_random_dl(yi, sei)
        base = dict(zip(group_cols, label)) if group_cols else {}
        rows.append({**base, "model": "fixed", **fixed})
        rows.append({**base, "model": "random_dl", **random})
    table = pd.DataFrame(rows)
    if group_cols:
        table = table.sort_values(group_cols + ["model"]).reset_index(drop=True)
    else:
        table = table.sort_values(["model"]).reset_index(drop=True)
    return MetaResult(table=table, details=details)

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import csv
import json
import itertools
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple
TRUE_SET = {"1","true","t","yes","y","on","enable","enabled"}
FALSE_SET = {"0","false","f","no","n","off","disable","disabled",""}

def _is_blank(x: Any) -> bool:
    return x is None or (isinstance(x, str) and x.strip() == "")

def parse_bool(x: Any, default: Optional[bool] = None) -> Optional[bool]:
    if x is None:
        return default
    if isinstance(x, bool):
        return x
    s = str(x).strip().lower()
    if s in TRUE_SET:
        return True
    if s in FALSE_SET:
        return False if s != "" else default
    raise ValueError(f"Invalid boolean: {x!r}")

def parse_number(x: Any) -> Optional[float]:
    if _is_blank(x):
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return float(x)
    s = str(x).strip().replace(",", "")
    try:
        return float(s)
    except Exception as e:
        raise ValueError(f"Invalid number: {x!r}") from e

def parse_jsonish(x: str) -> Any:
    s = x.strip()
    if s.startswith(("{" ,"[")):
        return json.loads(s)
    return None

def parse_listish(x: Any) -> Optional[List[Any]]:
    if _is_blank(x):
        return None
    if isinstance(x, list):
        return x
    if isinstance(x, (tuple, set)):
        return list(x)
    if isinstance(x, str):
        js = parse_jsonish(x)
        if isinstance(js, list):
            return js
        if "|" in x:
            parts = [p.strip() for p in x.split("|")]
        elif ";" in x:
            parts = [p.strip() for p in x.split(";")]
        else:
            return None
        parts = [p for p in parts if p != ""]
        return parts if parts else None
    return None

def coerce_scalar(x: Any) -> Any:
    if _is_blank(x):
        return None
    if isinstance(x, (int, float, bool, dict, list)):
        return x
    s = str(x).strip()
    js = parse_jsonish(s)
    if js is not None:
        return js
    b = None
    try:
        b = parse_bool(s, default=None)
    except Exception:
        b = None
    if b is not None:
        return b
    n = None
    try:
        n = parse_number(s)
    except Exception:
        n = None
    if n is not None:
        return n
    return s
@dataclass(frozen=True)
class Scenario:
    name: str
    inputs: Dict[str, Any]

def load_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rr = {k: (v if v is not None else "") for k, v in r.items()}
            rows.append(rr)
        return rows

def _normalize_keys(d: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        kk = (k or "").strip()
        if kk == "":
            continue
        out[kk] = v
    return out

def load_user_inputs_csv(path: Path) -> Dict[str, Any]:
    rows = load_csv_rows(path)
    if not rows:
        return {}
    if len(rows) > 1:
        raise ValueError("User inputs CSV must contain exactly one row of inputs.")
    raw = _normalize_keys(rows[0])
    parsed: Dict[str, Any] = {}
    for k, v in raw.items():
        if _is_blank(v):
            continue
        parsed[k] = coerce_scalar(v)
    return parsed
def parse_toggles(inputs: Mapping[str, Any], *, prefix: str = "toggle_") -> Dict[str, bool]:
    toggles: Dict[str, bool] = {}
    for k, v in inputs.items():
        if not isinstance(k, str):
            continue
        if k.lower().startswith(prefix):
            name = k[len(prefix):].strip() or k
            toggles[name] = bool(parse_bool(v, default=False))
    return toggles

def parse_sensitivity_grid(inputs: Mapping[str, Any], *, prefix: str = "sens_") -> Dict[str, List[Any]]:
    grid: Dict[str, List[Any]] = {}
    for k, v in inputs.items():
        if not isinstance(k, str):
            continue
        if not k.lower().startswith(prefix):
            continue
        name = k[len(prefix):].strip() or k
        lst = parse_listish(v)
        if lst is None:
            vv = coerce_scalar(v)
            if vv is None:
                continue
            grid[name] = [vv]
            continue
        coerced = [coerce_scalar(x) for x in lst]
        grid[name] = coerced
    return grid

def expand_scenarios(base_inputs: Mapping[str, Any], grid: Mapping[str, List[Any]], *, name_prefix: str = "scen") -> List[Scenario]:
    base = dict(base_inputs)
    if not grid:
        return [Scenario(name=f"{name_prefix}_0", inputs=base)]
    keys = list(grid.keys())
    vals = [grid[k] if grid[k] else [None] for k in keys]
    scenarios: List[Scenario] = []
    for idx, combo in enumerate(itertools.product(*vals)):
        inp = dict(base)
        parts = []
        for k, v in zip(keys, combo):
            inp[k] = v
            parts.append(f"{k}={v}")
        nm = f"{name_prefix}_{idx}"
        if parts:
            nm = nm + "__" + "_".join(parts)
        scenarios.append(Scenario(name=nm, inputs=inp))
    return scenarios
def validate_required(inputs: Mapping[str, Any], required: Iterable[str]) -> None:
    missing = [k for k in required if k not in inputs or _is_blank(inputs.get(k))]
    if missing:
        raise ValueError(f"Missing required inputs: {missing}")

def write_csv(path: Path, rows: List[Mapping[str, Any]], *, fieldnames: Optional[List[str]] = None) -> None:
    if not rows:
        raise ValueError("No rows to write.")
    if fieldnames is None:
        keys: List[str] = []
        seen = set()
        for r in rows:
            for k in r.keys():
                if k not in seen:
                    seen.add(k); keys.append(k)
        fieldnames = keys
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            out = {}
            for k in fieldnames:
                v = r.get(k, "")
                if v is None:
                    out[k] = ""
                elif isinstance(v, (dict, list)):
                    out[k] = json.dumps(v)
                else:
                    out[k] = v
            w.writerow(out)

def dump_json(path: Path, obj: Any, *, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=indent, ensure_ascii=False) + "\n", encoding="utf-8")

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))

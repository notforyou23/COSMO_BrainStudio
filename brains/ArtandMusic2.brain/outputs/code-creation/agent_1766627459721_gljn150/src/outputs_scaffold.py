from pathlib import Path
import json
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _resolve_within(root: Path, p: Path) -> Path:
    root_r = root.resolve()
    p_r = p.resolve()
    try:
        p_r.relative_to(root_r)
    except Exception as e:
        raise ValueError(f"Path escapes project root: {p_r} (root={root_r})") from e
    return p_r


def load_outputs_structure(config_path: Path) -> Dict[str, Any]:
    cp = Path(config_path)
    data = json.loads(cp.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("outputs_structure.json must contain a JSON object")
    return data


def _collect_paths(spec: Any) -> List[str]:
    paths: List[str] = []
    if spec is None:
        return paths
    if isinstance(spec, str):
        return [spec]
    if isinstance(spec, list):
        for item in spec:
            paths.extend(_collect_paths(item))
        return paths
    if isinstance(spec, dict):
        if "paths" in spec:
            paths.extend(_collect_paths(spec["paths"]))
        if "dirs" in spec:
            paths.extend(_collect_paths(spec["dirs"]))
        name = spec.get("name")
        children = spec.get("children")
        if isinstance(name, str) and children is not None:
            for child in _collect_paths(children):
                paths.append(str(Path(name) / child))
        return paths
    raise ValueError(f"Unsupported structure element type: {type(spec).__name__}")


def scaffold_outputs(
    project_root: Path,
    config_path: Optional[Path] = None,
    *,
    create: bool = True,
    verify: bool = True,
    strict: bool = False,
) -> Dict[str, Any]:
    pr = Path(project_root)
    cfg = Path(config_path) if config_path else pr / "config" / "outputs_structure.json"
    cfg_r = _resolve_within(pr, cfg)

    out: Dict[str, Any] = {
        "project_root": str(pr.resolve()),
        "config_path": str(cfg_r),
        "created": [],
        "existed": [],
        "missing": [],
        "verified_ok": None,
        "errors": [],
    }

    try:
        config = load_outputs_structure(cfg_r)
    except Exception as e:
        out["errors"].append(f"config_load_failed:{e}")
        out["verified_ok"] = False
        if strict:
            raise
        return out

    base_rel = config.get("base", "outputs")
    if not isinstance(base_rel, str) or not base_rel.strip():
        base_rel = "outputs"
    base_dir = _resolve_within(pr, pr / base_rel)

    raw_spec = config.get("structure", config.get("paths", config.get("dirs", [])))
    rel_paths = _collect_paths(raw_spec)
    rel_paths = [p for p in rel_paths if isinstance(p, str) and p.strip()]
    rel_paths = sorted(set(rel_paths))

    expected_dirs: List[Path] = [base_dir] + [_resolve_within(pr, base_dir / rp) for rp in rel_paths]

    if create:
        for d in expected_dirs:
            try:
                if d.exists():
                    if d.is_dir():
                        out["existed"].append(str(d))
                    else:
                        raise ValueError(f"expected directory but found file: {d}")
                else:
                    d.mkdir(parents=True, exist_ok=True)
                    out["created"].append(str(d))
            except Exception as e:
                out["errors"].append(f"create_failed:{d}:{e}")
                if strict:
                    raise

    if verify:
        missing: List[str] = []
        for d in expected_dirs:
            try:
                if not d.exists() or not d.is_dir():
                    missing.append(str(d))
            except Exception as e:
                out["errors"].append(f"verify_failed:{d}:{e}")
                if strict:
                    raise
        out["missing"] = missing
        out["verified_ok"] = (len(missing) == 0 and len(out["errors"]) == 0)
    else:
        out["verified_ok"] = (len(out["errors"]) == 0)

    out["base_dir"] = str(base_dir)
    out["expected_count"] = len(expected_dirs)
    return out


def verify_paths_exist(paths: Iterable[Path]) -> Tuple[bool, List[str]]:
    missing: List[str] = []
    for p in paths:
        pp = Path(p)
        if not pp.exists():
            missing.append(str(pp))
    return (len(missing) == 0, missing)

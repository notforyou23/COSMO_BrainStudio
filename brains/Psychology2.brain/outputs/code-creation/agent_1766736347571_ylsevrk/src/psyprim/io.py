from __future__ import annotations

from pathlib import Path
import json
from typing import Any, Dict, Tuple, Union


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        out = dict(base)
        for k, v in override.items():
            out[k] = _deep_merge(out.get(k), v) if k in out else v
        return out
    if isinstance(base, list) and isinstance(override, list):
        return list(override)
    return override


def _read_text(path: Union[str, Path]) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8")


def _maybe_json(text: str) -> Dict[str, Any]:
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("Overrides must be a JSON object (mapping).")
    return obj


def _simple_yaml_load(text: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "YAML overrides require PyYAML to be installed (pip install pyyaml)."
        ) from e
    obj = yaml.safe_load(text) or {}
    if not isinstance(obj, dict):
        raise ValueError("Overrides must be a YAML mapping/object.")
    return obj


def load_overrides(path: Union[str, Path, None]) -> Dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    text = _read_text(p).strip()
    if not text:
        return {}
    suf = p.suffix.lower()
    if suf in (".json",):
        return _maybe_json(text)
    if suf in (".yaml", ".yml"):
        return _simple_yaml_load(text)
    try:
        return _maybe_json(text)
    except Exception:
        return _simple_yaml_load(text)


def apply_overrides(roadmap: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    if not overrides:
        return dict(roadmap)
    if not isinstance(roadmap, dict) or not isinstance(overrides, dict):
        raise TypeError("roadmap and overrides must be dicts.")
    return _deep_merge(roadmap, overrides)


def _json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _yaml_scalar(x: Any) -> str:
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        return str(x)
    s = str(x)
    if s == "" or any(c in s for c in [":", "#", "\n", "\r", "\t"]) or s.strip() != s:
        s = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{s}"'
    return s


def _yaml_dump(obj: Any, indent: int = 0) -> str:
    sp = "  " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = []
        for k in sorted(obj.keys(), key=lambda x: str(x)):
            v = obj[k]
            key = _yaml_scalar(k)
            if isinstance(v, (dict, list)) and v:
                lines.append(f"{sp}{key}:")
                lines.append(_yaml_dump(v, indent + 1))
            else:
                lines.append(
                    f"{sp}{key}: {_yaml_dump(v, 0) if isinstance(v, (dict, list)) else _yaml_scalar(v)}"
                )
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        lines = []
        for item in obj:
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{sp}-")
                lines.append(_yaml_dump(item, indent + 1))
            else:
                lines.append(f"{sp}- {_yaml_scalar(item)}")
        return "\n".join(lines)
    return _yaml_scalar(obj)


def _md_escape(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _md_render(obj: Any, title: str = "Validation & Adoption Roadmap") -> str:
    lines = [f"# {_md_escape(title)}", ""]
    def render_value(key: str, val: Any, level: int) -> None:
        if isinstance(val, dict):
            lines.append(f'{"#"*(level)} {key}')
            lines.append("")
            for k in sorted(val.keys(), key=lambda x: str(x)):
                render_value(str(k), val[k], level + 1)
        elif isinstance(val, list):
            lines.append(f'{"#"*(level)} {key}')
            lines.append("")
            for item in val:
                if isinstance(item, dict):
                    name = str(item.get("name") or item.get("id") or item.get("title") or "Item")
                    lines.append(f"- **{_md_escape(name)}**")
                    for kk in sorted(item.keys(), key=lambda x: str(x)):
                        if str(kk) in ("name", "id", "title"):
                            continue
                        vv = item[kk]
                        if isinstance(vv, (dict, list)):
                            lines.append(f"  - {kk}:")
                            sub = _md_render(vv, title="").splitlines()
                            for s in sub:
                                if s.startswith("#") or s.strip() == "":
                                    continue
                                lines.append("    " + s)
                        else:
                            lines.append(f"  - {kk}: {_md_escape(str(vv))}")
                else:
                    lines.append(f"- {_md_escape(str(item))}")
            lines.append("")
        else:
            lines.append(f"- **{key}:** {_md_escape(str(val))}")
    if isinstance(obj, dict):
        for k in sorted(obj.keys(), key=lambda x: str(x)):
            v = obj[k]
            if isinstance(v, (dict, list)):
                render_value(str(k), v, 2)
            else:
                render_value(str(k), v, 2)
                lines.append("")
    else:
        lines.append(_md_escape(str(obj)))
        lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    return text


def write_artifacts(
    roadmap: Dict[str, Any],
    out_dir: Union[str, Path],
    basename: str = "roadmap",
    title: str = "Validation & Adoption Roadmap",
) -> Tuple[Path, Path, Path]:
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)
    json_path = outp / f"{basename}.json"
    yaml_path = outp / f"{basename}.yaml"
    md_path = outp / f"{basename}.md"
    json_path.write_text(_json_dumps(roadmap), encoding="utf-8")
    yaml_path.write_text(_yaml_dump(roadmap).rstrip() + "\n", encoding="utf-8")
    md_path.write_text(_md_render(roadmap, title=title), encoding="utf-8")
    return json_path, yaml_path, md_path

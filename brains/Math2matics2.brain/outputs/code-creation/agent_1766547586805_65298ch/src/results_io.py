from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple, Union
import hashlib
import io
import json
import os
import sys
def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Union[str, Path], chunk_size: int = 1024 * 1024) -> str:
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    tmp.replace(path)
def _json_dumps_canonical(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _validate_minimal_payload(payload: Mapping[str, Any]) -> None:
    if not isinstance(payload, Mapping):
        raise TypeError("results payload must be a mapping")
    if "schema_version" not in payload or not isinstance(payload["schema_version"], str):
        raise ValueError("results payload must include string field 'schema_version'")
    if "run" in payload and not isinstance(payload["run"], Mapping):
        raise ValueError("if present, 'run' must be an object/mapping")
    if "artifacts" in payload and not isinstance(payload["artifacts"], Mapping):
        raise ValueError("if present, 'artifacts' must be an object/mapping")


def validate_results_payload(payload: Mapping[str, Any], schema_path: Optional[Union[str, Path]] = None) -> None:
    _validate_minimal_payload(payload)
    if schema_path is None:
        return
    try:
        import jsonschema  # type: ignore
    except Exception:
        return
    sp = Path(schema_path)
    if not sp.is_file():
        return
    schema = json.loads(sp.read_text(encoding="utf-8"))
    jsonschema.validate(instance=dict(payload), schema=schema)
def save_matplotlib_figure(
    fig: Any,
    path: Union[str, Path],
    *,
    dpi: int = 150,
    facecolor: str = "white",
    bbox_inches: Union[str, None] = "tight",
    pad_inches: float = 0.1,
) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    savefig_kwargs: Dict[str, Any] = dict(
        format=p.suffix.lstrip(".").lower() or "png",
        dpi=dpi,
        facecolor=facecolor,
        bbox_inches=bbox_inches,
        pad_inches=pad_inches,
    )
    fmt = savefig_kwargs["format"]
    if fmt in {"png"}:
        savefig_kwargs["metadata"] = {}
    fig.savefig(buf, **savefig_kwargs)
    data = buf.getvalue()
    _atomic_write_bytes(p, data)
    return p
@dataclass(frozen=True)
class WrittenArtifacts:
    results_json: Path
    results_sha256: str
    artifact_hashes: Dict[str, str]


def write_results(
    outputs_dir: Union[str, Path],
    payload: Dict[str, Any],
    *,
    figures: Optional[Mapping[str, Any]] = None,
    schema_path: Optional[Union[str, Path]] = None,
    results_filename: str = "results.json",
) -> WrittenArtifacts:
    outdir = Path(outputs_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    figures = figures or {}
    artifact_hashes: Dict[str, str] = {}
    artifacts_obj: Dict[str, Any] = dict(payload.get("artifacts") or {})
    fig_dir = outdir / "figures"
    fig_entries: Dict[str, Any] = {}

    for name, fig in figures.items():
        safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in str(name)).strip("_") or "figure"
        fname = safe
        if "." not in fname:
            fname += ".png"
        fpath = fig_dir / fname
        if hasattr(fig, "savefig"):
            save_matplotlib_figure(fig, fpath)
        elif isinstance(fig, (str, Path)) and Path(fig).is_file():
            src = Path(fig)
            fpath.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_bytes(fpath, src.read_bytes())
        else:
            raise TypeError(f"Unsupported figure type for {name!r}")
        h = sha256_file(fpath)
        artifact_hashes[str(fpath.relative_to(outdir))] = h
        fig_entries[name] = {"path": str(fpath.relative_to(outdir)), "sha256": h}

    if fig_entries:
        artifacts_obj.setdefault("figures", fig_entries)

    payload = dict(payload)
    if artifacts_obj:
        payload["artifacts"] = artifacts_obj

    validate_results_payload(payload, schema_path=schema_path)

    results_path = outdir / results_filename
    results_text = _json_dumps_canonical(payload)
    results_bytes = results_text.encode("utf-8")
    _atomic_write_bytes(results_path, results_bytes)
    results_hash = _sha256_bytes(results_bytes)

    payload2 = json.loads(results_path.read_text(encoding="utf-8"))
    artifacts_obj2: Dict[str, Any] = dict(payload2.get("artifacts") or {})
    hashes_obj: Dict[str, Any] = dict(artifacts_obj2.get("hashes") or {})
    hashes_obj["results.json"] = results_hash
    for k, v in artifact_hashes.items():
        hashes_obj[k] = v
    artifacts_obj2["hashes"] = hashes_obj
    payload2["artifacts"] = artifacts_obj2

    validate_results_payload(payload2, schema_path=schema_path)
    results_text2 = _json_dumps_canonical(payload2)
    results_bytes2 = results_text2.encode("utf-8")
    _atomic_write_bytes(results_path, results_bytes2)
    results_hash2 = _sha256_bytes(results_bytes2)

    return WrittenArtifacts(results_json=results_path, results_sha256=results_hash2, artifact_hashes=artifact_hashes)

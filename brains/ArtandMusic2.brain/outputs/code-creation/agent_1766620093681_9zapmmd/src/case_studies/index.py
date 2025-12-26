from __future__ import annotations

from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional, Tuple, Union
import json


JSONObj = Union[dict, list, str, int, float, bool, None]


def _read_json_ordered(path: Path) -> OrderedDict:
    if not path.exists():
        return OrderedDict()
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return OrderedDict()
    return json.loads(text, object_pairs_hook=OrderedDict)


def _write_json_ordered(path: Path, obj: JSONObj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, ensure_ascii=False, indent=2)
    path.write_text(data.rstrip() + "\n", encoding="utf-8")


def _find_artifacts_container(index: MutableMapping[str, Any]) -> Tuple[str, list]:
    # Preferred shape: {"artifacts": [ ... ]} (append-only, order-preserving)
    if isinstance(index.get("artifacts"), list):
        return "artifacts", index["artifacts"]
    # Alternate legacy: {"ARTIFACT_INDEX": [ ... ]}
    if isinstance(index.get("ARTIFACT_INDEX"), list):
        return "ARTIFACT_INDEX", index["ARTIFACT_INDEX"]
    # Create canonical container if none present
    index["artifacts"] = []
    return "artifacts", index["artifacts"]


def load_artifact_index(index_path: Union[str, Path]) -> OrderedDict:
    """Load ARTIFACT_INDEX JSON as an ordered mapping.

    Supports multiple historical shapes; callers should treat the returned object
    as mutable and pass it back to save_artifact_index().
    """
    p = Path(index_path)
    idx = _read_json_ordered(p)
    if not isinstance(idx, OrderedDict):
        idx = OrderedDict(idx) if isinstance(idx, dict) else OrderedDict()
    _find_artifacts_container(idx)  # ensure container exists
    return idx


def save_artifact_index(index_path: Union[str, Path], index: Mapping[str, Any]) -> None:
    _write_json_ordered(Path(index_path), index)


def _artifact_id(artifact: Mapping[str, Any]) -> Optional[str]:
    v = artifact.get("id") if isinstance(artifact, Mapping) else None
    return v if isinstance(v, str) and v.strip() else None


def _iter_existing_ids(artifacts: Iterable[Any]) -> Iterable[str]:
    for a in artifacts:
        if isinstance(a, Mapping):
            aid = _artifact_id(a)
            if aid:
                yield aid


def add_case_study_to_index(
    index_path: Union[str, Path],
    artifact: Mapping[str, Any],
) -> bool:
    """Idempotently append a case-study artifact entry to ARTIFACT_INDEX.

    Returns True if an entry was added, False if it already existed.
    Preserves existing ordering and does not mutate existing entries.
    """
    aid = _artifact_id(artifact)
    if not aid:
        raise ValueError("artifact must include a non-empty string 'id' field")

    idx = load_artifact_index(index_path)
    _, artifacts = _find_artifacts_container(idx)

    existing = set(_iter_existing_ids(artifacts))
    if aid in existing:
        return False

    artifacts.append(OrderedDict(artifact.items()))
    save_artifact_index(index_path, idx)
    return True

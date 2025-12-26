from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Iterable, List, Dict, Optional, Tuple


@dataclass(frozen=True)
class ArtifactMeta:
    rel_path: str
    bytes: int
    mtime_utc: str
    sha256_12: str


def _utc_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_file(path: Path, max_bytes: Optional[int] = None) -> str:
    h = sha256()
    n = 0
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            if max_bytes is not None and n + len(chunk) > max_bytes:
                chunk = chunk[: max_bytes - n]
            h.update(chunk)
            n += len(chunk)
            if max_bytes is not None and n >= max_bytes:
                break
    return h.hexdigest()


def _collect_artifacts(outputs_dir: Path) -> List[ArtifactMeta]:
    if not outputs_dir.exists():
        return []
    items: List[ArtifactMeta] = []
    for p in sorted(outputs_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(outputs_dir).as_posix()
        if rel == "ARTIFACT_INDEX.md":
            continue
        st = p.stat()
        digest = _hash_file(p, max_bytes=10 * 1024 * 1024)[:12]
        items.append(ArtifactMeta(rel, int(st.st_size), _utc_iso(st.st_mtime), digest))
    return items


def _group(items: Iterable[ArtifactMeta]) -> Dict[str, List[ArtifactMeta]]:
    groups: Dict[str, List[ArtifactMeta]] = {}
    for it in items:
        top = it.rel_path.split("/", 1)[0] if "/" in it.rel_path else "."
        groups.setdefault(top, []).append(it)
    for k in list(groups.keys()):
        groups[k] = sorted(groups[k], key=lambda x: x.rel_path)
    return dict(sorted(groups.items(), key=lambda kv: (kv[0] != ".", kv[0])))


def _md_escape(s: str) -> str:
    return s.replace("|", "\|")


def render_artifact_index(outputs_dir: Path) -> str:
    items = _collect_artifacts(outputs_dir)
    groups = _group(items)
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines: List[str] = []
    lines.append("# ARTIFACT INDEX")
    lines.append("")
    lines.append("Canonical outputs inventory generated from `outputs/` only.")
    lines.append(f"- Generated (UTC): `{generated}`")
    lines.append(f"- Root: `{outputs_dir.as_posix()}`")
    lines.append("")
    if not items:
        lines.append("_No artifacts found under `outputs/`._")
        lines.append("")
        return "\n".join(lines)

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total files: **{len(items)}**")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    for group_name, group_items in groups.items():
        title = "Root" if group_name == "." else group_name
        anchor = title.lower().replace(" ", "-")
        lines.append(f"### {title}")
        lines.append("")
        lines.append("| Path (canonical) | Bytes | Modified (UTC) | SHA256 (12) |")
        lines.append("|---|---:|---|---|")
        for it in group_items:
            canon = f"outputs/{it.rel_path}"
            lines.append(
                f"| `{_md_escape(canon)}` | {it.bytes} | `{it.mtime_utc}` | `{it.sha256_12}` |"
            )
        lines.append("")
    return "\n".join(lines)


def write_artifact_index(repo_root: Path, outputs_subdir: str = "outputs") -> Path:
    outputs_dir = repo_root / outputs_subdir
    outputs_dir.mkdir(parents=True, exist_ok=True)
    out_path = outputs_dir / "ARTIFACT_INDEX.md"
    out_path.write_text(render_artifact_index(outputs_dir), encoding="utf-8")
    return out_path


def main(argv: Optional[List[str]] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Generate outputs/ARTIFACT_INDEX.md from canonical outputs/ tree.")
    p.add_argument("--repo-root", default=".", help="Repository root containing outputs/ (default: .)")
    p.add_argument("--outputs-subdir", default="outputs", help="Outputs directory name (default: outputs)")
    args = p.parse_args(argv)

    out = write_artifact_index(Path(args.repo_root).resolve(), outputs_subdir=args.outputs_subdir)
    print(out.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

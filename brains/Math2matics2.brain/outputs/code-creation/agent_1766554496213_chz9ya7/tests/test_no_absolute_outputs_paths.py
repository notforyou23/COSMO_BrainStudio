from __future__ import annotations

from pathlib import Path
import re


def _repo_root() -> Path:
    # tests/ is expected at repo_root/tests
    return Path(__file__).resolve().parents[1]


def _output_dir() -> Path:
    return _repo_root() / "outputs"


def _iter_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file()]


def _read_text(p: Path, max_bytes: int = 2_000_000) -> str:
    try:
        with p.open("rb") as f:
            data = f.read(max_bytes + 1)
        if len(data) > max_bytes:
            data = data[:max_bytes]
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def test_expected_artifacts_under_outputs_dir() -> None:
    out_dir = _output_dir()
    assert out_dir.exists() and out_dir.is_dir(), f"Missing expected repo-relative outputs dir: {out_dir}"

    files = _iter_files(out_dir)
    assert files, f"No artifacts found under {out_dir}; expected at least one output file."

    key_exts = {".json", ".log", ".txt", ".md", ".csv", ".html"}
    has_key = any(p.suffix.lower() in key_exts for p in files)
    assert has_key, f"Found outputs under {out_dir}, but none with expected extensions {sorted(key_exts)}."


def test_no_absolute_root_outputs_paths_in_artifacts_or_logs() -> None:
    out_dir = _output_dir()
    files = _iter_files(out_dir)
    assert files, f"No files to scan under {out_dir}; cannot validate output path hygiene."

    # Detect absolute root-level /outputs references (not repo-relative ./outputs or <repo>/outputs).
    pat = re.compile(r"(^|[^A-Za-z0-9_])(/outputs)(/|\|\b)", re.MULTILINE)

    offenders: list[tuple[str, str]] = []
    for p in files:
        text = _read_text(p)
        if not text:
            continue
        m = pat.search(text)
        if m:
            start = max(0, m.start(2) - 60)
            end = min(len(text), m.end(2) + 60)
            snippet = text[start:end].replace("\n", "\\n")
            offenders.append((str(p.relative_to(out_dir)), snippet))

    assert not offenders, "Found absolute '/outputs' paths in artifacts/logs:\n" + "\n".join(
        f"- {rel}: ...{snip}..." for rel, snip in offenders[:25]
    )

from __future__ import annotations

from pathlib import Path
import os
import re


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _iter_candidate_files(root: Path):
    # Scan likely artifact/log locations without traversing the whole repo.
    candidates = []
    for rel in ("outputs", "output", "logs", "log", ".pytest_cache"):
        p = root / rel
        if p.exists():
            candidates.append(p)

    # Also include top-level log-ish files.
    for pat in ("*.log", "*.txt", "*.json", "*.jsonl"):
        candidates.extend(root.glob(pat))

    seen = set()
    for c in candidates:
        if c.is_file():
            if c in seen:
                continue
            seen.add(c)
            yield c
        elif c.is_dir():
            for f in c.rglob("*"):
                if not f.is_file():
                    continue
                if any(part in {".git", "__pycache__", ".venv", "venv", "site-packages"} for part in f.parts):
                    continue
                if f.suffix.lower() not in {".log", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".md", ".yaml", ".yml"}:
                    continue
                if f in seen:
                    continue
                seen.add(f)
                yield f


_ABS_POSIX_TOKEN = re.compile(r'/(?:[^\s"\'<>|]+)')
_ABS_WIN_TOKEN = re.compile(r"[A-Za-z]:\\[^\s\"\'<>\|]+")
_OUT_SEGMENT = re.compile(r"(^|/|\\)outputs($|/|\\)")


def _find_absolute_outputs_paths(text: str):
    hits = []
    for m in _ABS_POSIX_TOKEN.finditer(text):
        tok = m.group(0)
        if _OUT_SEGMENT.search(tok):
            hits.append(tok)
    for m in _ABS_WIN_TOKEN.finditer(text):
        tok = m.group(0)
        if _OUT_SEGMENT.search(tok.replace("\\", "/")) or _OUT_SEGMENT.search(tok):
            hits.append(tok)
    return hits


def test_no_absolute_outputs_paths_in_logs_or_artifacts():
    root = _project_root()

    # Best-effort: avoid false failures if a user explicitly chooses an absolute OUTPUT_DIR.
    # This test specifically guards against hardcoded absolute paths that include a '/outputs' segment.
    env_out = os.environ.get("OUTPUT_DIR", "")
    allow_env_out = bool(env_out) and (env_out.startswith("/") or re.match(r"^[A-Za-z]:\\", env_out or ""))

    findings = []
    for fp in _iter_candidate_files(root):
        try:
            if fp.stat().st_size > 2_000_000:
                continue
            text = fp.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for hit in _find_absolute_outputs_paths(text):
            # If the user explicitly set OUTPUT_DIR to an absolute path containing /outputs,
            # don't flag that exact prefix; still flag other absolute /outputs occurrences.
            if allow_env_out:
                norm_hit = hit.replace("\\", "/")
                norm_env = env_out.replace("\\", "/")
                if norm_env and norm_hit.startswith(norm_env):
                    continue
            findings.append((str(fp.relative_to(root)), hit))

    assert not findings, "Found absolute paths containing an 'outputs' segment (should be relative or derived):\n" + "\n".join(
        f"- {f}: {h}" for f, h in findings[:50]
    )

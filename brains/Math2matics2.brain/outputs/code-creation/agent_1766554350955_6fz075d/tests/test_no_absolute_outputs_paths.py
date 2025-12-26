from __future__ import annotations

from pathlib import Path
import re


def _find_repo_root(start: Path) -> Path:
    p = start.resolve()
    for parent in [p, *p.parents]:
        if (parent / "pyproject.toml").exists() or (parent / "setup.cfg").exists() or (parent / ".git").exists():
            return parent
    return start.resolve().parents[1]  # reasonable fallback: repo_root/tests/test_*.py -> repo_root


def _iter_python_files(repo_root: Path):
    # Scan typical source/test locations; fall back to scanning the whole repo if none exist.
    candidates = [repo_root / "src", repo_root / "tests"]
    roots = [p for p in candidates if p.exists() and p.is_dir()]
    if not roots:
        roots = [repo_root]
    for root in roots:
        for path in root.rglob("*.py"):
            if any(part.startswith(".") for part in path.parts):
                continue
            yield path


# Matches any literal string beginning with /outputs (absolute path). Examples:
# "/outputs", '/outputs/', f"/outputs/{x}", Path("/outputs")
ABS_OUTPUTS_LITERAL_RE = re.compile(r'''(?P<q>["'])/outputs(?:/|\b)''')


def test_no_absolute_outputs_paths():
    repo_root = _find_repo_root(Path(__file__).parent)
    this_file = Path(__file__).resolve()

    offenders = []
    for py_file in _iter_python_files(repo_root):
        if py_file.resolve() == this_file:
            continue
        try:
            text = py_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = py_file.read_text(encoding="utf-8", errors="ignore")

        # Ignore occurrences inside URLs like "http://.../outputs"
        for m in ABS_OUTPUTS_LITERAL_RE.finditer(text):
            i = m.start()
            prefix = text[max(0, i - 12) : i]
            if "://" in prefix:
                continue
            line_no = text.count("\n", 0, i) + 1
            offenders.append(f"{py_file.relative_to(repo_root)}:{line_no}")

    assert not offenders, (
        "Found absolute '/outputs' references in Python code. "
        "Use the centralized OUTPUT_DIR resolver instead. Offenders:\n- "
        + "\n- ".join(offenders)
    )

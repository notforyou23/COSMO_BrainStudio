import re
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in (here.parent, *here.parents):
        if (p / ".git").exists():
            return p
    return Path.cwd().resolve()


def _git_tracked_files(root: Path):
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "ls-files"],
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception:
        return None
    files = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        p = (root / line).resolve()
        if p.is_file():
            files.append(p)
    return files


def _fallback_files(root: Path):
    allow_ext = {".py", ".yml", ".yaml", ".toml", ".ini", ".sh"}
    files = []
    for base in (root / "src", root / "tests"):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in allow_ext:
                files.append(p.resolve())
    return files


def test_no_absolute_outputs_path_usage():
    root = _repo_root()
    files = _git_tracked_files(root) or _fallback_files(root)
    # Only scan likely code/config; ignore generated outputs.
    allow_ext = {".py", ".yml", ".yaml", ".toml", ".ini", ".sh"}
    files = [p for p in files if p.suffix in allow_ext and "outputs" not in p.parts]

    abs_outputs = "/" + "outputs"
    pat = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(abs_outputs) + r"(?:/|\b)")

    bad = []
    this_file = Path(__file__).resolve()
    for p in files:
        if p.resolve() == this_file:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if pat.search(text):
            bad.append(str(p.relative_to(root)))
            if len(bad) >= 25:
                break

    assert not bad, (
        "Absolute '/outputs' path usage is forbidden; use the output-path helper and "
        "a relative './outputs' (or OUTPUT_DIR override). Offenders:\n- "
        + "\n- ".join(bad)
    )

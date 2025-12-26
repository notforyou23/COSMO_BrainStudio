from pathlib import Pathimport json
import os
import subprocess
import sys
import os
os.chdir(r'/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _w(p: Path, s: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def _run_cli(args, cwd: Path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    cp = subprocess.run(
        [sys.executable, "-m", "src.cli.path_canonicalize", *args],
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert cp.returncode == 0, f"rc={cp.returncode}\nSTDOUT:\n{cp.stdout}\nSTDERR:\n{cp.stderr}"
    return cp


def test_sync_duplicates_rewrite_and_report(tmp_path: Path):
    repo = tmp_path
    rt = repo / "runtime" / "outputs"
    out = repo / "outputs"

    _w(rt / "reports" / "a.md", "# A\nsee runtime/outputs/reports/a.md\n")
    _w(rt / "schemas" / "x.json", json.dumps({"x": 1}))
    _w(out / "reports" / "dup.md", "same\n")
    _w(rt / "reports" / "dup.md", "same\n")
    _w(repo / "docs.md", "link: runtime/outputs/reports/a.md\n")

    _run_cli(["--repo-root", str(repo), "--rewrite-refs"], cwd=repo)

    assert (out / "reports" / "a.md").is_file()
    assert (out / "schemas" / "x.json").is_file()
    assert (out / "reports" / "dup.md").read_text(encoding="utf-8") == "same\n"

    docs = (repo / "docs.md").read_text(encoding="utf-8")
    assert "outputs/reports/a.md" in docs
    assert "runtime/outputs/reports/a.md" not in docs

    report = out / "qa" / "path_canonicalization_report.md"
    assert report.is_file()
    rtxt = report.read_text(encoding="utf-8")
    assert "runtime/outputs" in rtxt and "outputs" in rtxt
    assert ("a.md" in rtxt) and ("x.json" in rtxt)
    assert "dup.md" in rtxt and ("duplicate" in rtxt.lower() or "dedup" in rtxt.lower())


def test_dry_run_makes_no_fs_changes_but_emits_report(tmp_path: Path):
    repo = tmp_path
    rt = repo / "runtime" / "outputs"
    out = repo / "outputs"
    _w(rt / "tools" / "t.py", "print('x')\n")
    assert not (out / "tools" / "t.py").exists()

    _run_cli(["--repo-root", str(repo), "--dry-run"], cwd=repo)

    assert not (out / "tools" / "t.py").exists()
    report = out / "qa" / "path_canonicalization_report.md"
    assert report.is_file()
    rtxt = report.read_text(encoding="utf-8").lower()
    assert "dry" in rtxt and "run" in rtxt

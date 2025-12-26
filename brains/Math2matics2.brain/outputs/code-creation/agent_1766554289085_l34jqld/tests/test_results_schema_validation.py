from pathlib import Path
import json
import os
import sys
import subprocess
import inspect
import pytest


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _ensure_src_on_path() -> Path:
    root = _project_root()
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    return root


def _fixed_results_path(root: Path) -> Path:
    return root / "outputs" / "toy_experiment" / "results.json"


def _invoke_entrypoint(root: Path) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

    try:
        import main  # type: ignore

        if hasattr(main, "main") and callable(main.main):
            sig = inspect.signature(main.main)
            if len(sig.parameters) == 0:
                main.main()
            else:
                main.main([])
            return

        if hasattr(main, "cli") and callable(main.cli):
            sig = inspect.signature(main.cli)
            if len(sig.parameters) == 0:
                main.cli()
            else:
                main.cli([])
            return
    except Exception:
        pass

    subprocess.run(
        [sys.executable, "-m", "main"],
        cwd=str(root),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _validate_schema(data: object) -> None:
    import toy_experiment.results_schema as rs  # type: ignore

    if hasattr(rs, "validate_results") and callable(rs.validate_results):
        out = rs.validate_results(data)
        if isinstance(out, bool):
            assert out is True
        return
    if hasattr(rs, "validate") and callable(rs.validate):
        out = rs.validate(data)
        if isinstance(out, bool):
            assert out is True
        return
    raise AssertionError("Expected toy_experiment.results_schema to expose validate_results(data) or validate(data)")


def test_results_artifact_written_and_valid_schema(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _ensure_src_on_path()
    results_path = _fixed_results_path(root)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    if results_path.exists():
        results_path.unlink()

    _invoke_entrypoint(root)

    assert results_path.exists() and results_path.is_file()
    data = json.loads(results_path.read_text(encoding="utf-8"))
    _validate_schema(data)

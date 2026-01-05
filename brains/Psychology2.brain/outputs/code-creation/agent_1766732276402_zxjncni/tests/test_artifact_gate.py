import importlib
import inspect
from pathlib import Path

import pytest


def _load_module():
    try:
        return importlib.import_module("src.artifact_gate")
    except Exception as e:
        pytest.fail(f"Failed to import src.artifact_gate: {e!r}")


def _call_best(module, names, base_dir, version=None):
    for name in names:
        fn = getattr(module, name, None)
        if not callable(fn):
            continue
        sig = inspect.signature(fn)
        kwargs = {}
        for p in sig.parameters.values():
            if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                continue
            if p.name in ("base_dir", "root", "project_root", "workdir", "repo_root", "path"):
                kwargs[p.name] = Path(base_dir)
            elif version is not None and p.name in ("version", "cycle_version", "release", "tag"):
                kwargs[p.name] = version
        try:
            return fn(**kwargs)
        except TypeError:
            try:
                return fn(Path(base_dir), version) if version is not None else fn(Path(base_dir))
            except TypeError:
                return fn()
    pytest.fail(f"None of the expected callables exist: {names}")


def _create_outputs(module, base_dir, version=None):
    return _call_best(
        module,
        ["create_outputs_structure", "create_outputs", "ensure_outputs", "init_outputs", "create_structure"],
        base_dir,
        version=version,
    )


def _check_outputs(module, base_dir):
    return _call_best(
        module,
        ["verify_artifacts", "check_artifacts", "verify_outputs", "validate_outputs", "assert_outputs_ready"],
        base_dir,
        version=None,
    )


def _outputs_dir(base_dir: Path) -> Path:
    return Path(base_dir) / "outputs"


@pytest.mark.parametrize("version", [None, "0.1.0"])
def test_creates_structure_and_nonempty_files(tmp_path, version):
    m = _load_module()
    _create_outputs(m, tmp_path, version=version)

    out = _outputs_dir(tmp_path)
    assert out.exists() and out.is_dir()

    readme = out / "README.md"
    changelog = out / "CHANGELOG.md"
    for p in (readme, changelog):
        assert p.exists() and p.is_file()
        assert p.read_text(encoding="utf-8").strip() != ""

    subdirs = [p for p in out.iterdir() if p.is_dir()]
    assert len(subdirs) >= 1

    _check_outputs(m, tmp_path)


def test_verify_fails_when_required_missing_or_empty(tmp_path):
    m = _load_module()
    _create_outputs(m, tmp_path, version="0.1.0")
    out = _outputs_dir(tmp_path)

    (out / "README.md").write_text("", encoding="utf-8")
    with pytest.raises(Exception):
        _check_outputs(m, tmp_path)

    _create_outputs(m, tmp_path, version="0.1.0")
    (out / "README.md").unlink()
    with pytest.raises(Exception):
        _check_outputs(m, tmp_path)


def test_changelog_versioning_behavior(tmp_path):
    m = _load_module()
    _create_outputs(m, tmp_path, version="0.1.0")
    out = _outputs_dir(tmp_path)
    cpath = out / "CHANGELOG.md"
    first = cpath.read_text(encoding="utf-8")
    assert "0.1.0" in first

    _create_outputs(m, tmp_path, version="0.1.1")
    second = cpath.read_text(encoding="utf-8")
    assert "0.1.0" in second and "0.1.1" in second
    assert len(second) >= len(first)

    _check_outputs(m, tmp_path)

import os
from pathlib import Path

import pytest

from src.utils.paths import outputs_path


def _can_write_dir(p: Path) -> bool:
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def test_outputs_path_default_location_and_is_writable(monkeypatch):
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    p = outputs_path()
    assert isinstance(p, Path)
    assert p.exists() and p.is_dir()
    assert p.name == "outputs" or p.as_posix().endswith("/outputs")
    assert _can_write_dir(p)


def test_outputs_path_respects_output_dir_override(monkeypatch, tmp_path):
    custom = tmp_path / "custom_outputs_dir"
    monkeypatch.setenv("OUTPUT_DIR", str(custom))
    p = outputs_path()
    assert p == custom
    assert p.exists() and p.is_dir()
    assert _can_write_dir(p)


def test_outputs_path_creates_missing_output_dir(monkeypatch, tmp_path):
    custom = tmp_path / "nested" / "outputs"
    assert not custom.exists()
    monkeypatch.setenv("OUTPUT_DIR", str(custom))
    p = outputs_path()
    assert p == custom
    assert p.exists() and p.is_dir()


def test_outputs_path_fails_when_output_dir_is_a_file(monkeypatch, tmp_path):
    f = tmp_path / "not_a_dir"
    f.write_text("x", encoding="utf-8")
    monkeypatch.setenv("OUTPUT_DIR", str(f))
    with pytest.raises((NotADirectoryError, FileExistsError, OSError, ValueError)):
        outputs_path()


def test_outputs_path_fails_when_output_dir_unwritable(monkeypatch, tmp_path):
    d = tmp_path / "unwritable"
    d.mkdir()
    try:
        d.chmod(0o555)
    except Exception:
        pytest.skip("chmod not supported for this environment")
    monkeypatch.setenv("OUTPUT_DIR", str(d))
    try:
        with pytest.raises((PermissionError, OSError)):
            outputs_path()
    finally:
        try:
            d.chmod(0o755)
        except Exception:
            pass

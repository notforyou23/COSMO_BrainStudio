import json
from pathlib import Path
import pytest

try:
    from src.determinism import sha256sum_bytes, sha256sum_path
except Exception as e:  # pragma: no cover
    sha256sum_bytes = sha256sum_path = None
    _det_import_err = e

try:
    from src.io_utils import atomic_write_bytes, atomic_write_text, stable_json_dumps
except Exception as e:  # pragma: no cover
    atomic_write_bytes = atomic_write_text = stable_json_dumps = None
    _io_import_err = e


def _req(obj, err, name: str):
    if obj is None:
        raise AssertionError(f"Missing required API {name}: {err!r}")


def test_sha256sum_bytes_known_vector():
    _req(sha256sum_bytes, globals().get("_det_import_err"), "src.determinism.sha256sum_bytes")
    assert sha256sum_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert sha256sum_bytes(b"abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sha256sum_path_matches_bytes(tmp_path: Path):
    _req(sha256sum_bytes, globals().get("_det_import_err"), "src.determinism.sha256sum_bytes")
    _req(sha256sum_path, globals().get("_det_import_err"), "src.determinism.sha256sum_path")
    p = tmp_path / "a.bin"
    data = b"hello\nworld\n"
    p.write_bytes(data)
    assert sha256sum_path(p) == sha256sum_bytes(data)


def test_atomic_write_bytes_is_deterministic_and_no_temp_left(tmp_path: Path):
    _req(atomic_write_bytes, globals().get("_io_import_err"), "src.io_utils.atomic_write_bytes")
    p = tmp_path / "out.bin"
    data = b"0123456789" * 1000
    atomic_write_bytes(p, data)
    h1 = p.read_bytes()
    atomic_write_bytes(p, data)
    h2 = p.read_bytes()
    assert h1 == h2 == data
    leftovers = [x for x in tmp_path.iterdir() if x.is_file() and x.name != "out.bin"]
    assert leftovers == []


def test_stable_json_bytes_and_hash_repeatable(tmp_path: Path):
    _req(stable_json_dumps, globals().get("_io_import_err"), "src.io_utils.stable_json_dumps")
    _req(atomic_write_text, globals().get("_io_import_err"), "src.io_utils.atomic_write_text")
    _req(sha256sum_bytes, globals().get("_det_import_err"), "src.determinism.sha256sum_bytes")

    obj = {"b": 2, "a": [3, 2, 1], "nested": {"z": None, "y": True, "x": "µ"}}
    s1 = stable_json_dumps(obj)
    s2 = stable_json_dumps(obj)
    assert s1 == s2

    p = tmp_path / "results.json"
    atomic_write_text(p, s1, encoding="utf-8")
    b1 = p.read_bytes()
    atomic_write_text(p, s2, encoding="utf-8")
    b2 = p.read_bytes()
    assert b1 == b2
    assert sha256sum_bytes(b1) == sha256sum_bytes(b2)

    # Ensure the stable JSON is parseable and semantically identical.
    assert json.loads(b1.decode("utf-8")) == obj

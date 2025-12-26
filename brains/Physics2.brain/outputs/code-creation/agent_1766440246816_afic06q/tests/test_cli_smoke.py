import inspect
import sys

import pytest


def _invoke_cli(monkeypatch, args):
    # Import inside to ensure import-time errors are surfaced by this test.
    import qg_bench.cli as cli

    main = getattr(cli, "main", None)
    assert callable(main), "qg_bench.cli.main must be callable"

    sig = inspect.signature(main)
    if len(sig.parameters) >= 1:
        return main(args)

    monkeypatch.setattr(sys, "argv", ["qg-bench", *args], raising=False)
    return main()
def test_qg_bench_help(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _invoke_cli(monkeypatch, ["--help"])
    assert exc.value.code in (0, None)

    out = capsys.readouterr().out.lower()
    assert "usage" in out or "help" in out
def test_qg_bench_version(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        _invoke_cli(monkeypatch, ["--version"])
    assert exc.value.code in (0, None)

    out = capsys.readouterr().out.strip()
    # Accept any non-empty version string as long as the path executes.
    assert out !=

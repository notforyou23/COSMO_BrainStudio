"""
runtime.outputs.tools package.

This package contains CLI-style utilities that manage and validate files produced in
the runtime/outputs workspace.

Primary entrypoint:
- runtime.outputs.tools.validate_outputs
"""

from __future__ import annotations

__all__ = ["run_validate"]

def run_validate(argv: list[str] | None = None) -> int:
    """Run the validate_outputs CLI tool.

    Args:
        argv: Optional argument vector (excluding program name). If None, the tool
            will read arguments from sys.argv.

    Returns:
        Process-style exit code (0 for success).
    """
    from .validate_outputs import main as _main  # local import to keep package light
    return int(_main(argv))

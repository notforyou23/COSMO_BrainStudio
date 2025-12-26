"""Ultra-lightweight minimal test probes for QA container validation.

This module defines a small set of commands intended to:
- minimize test discovery overhead (single-file pytest/unittest),
- validate that the container can execute Python,
- validate that logs can be written under /outputs/qa/logs/.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import json
import os
import shlex
CONTAINER_LOG_DIR = "/outputs/qa/logs"


@dataclass(frozen=True)
class ProbeCommand:
    name: str
    argv: List[str]
    timeout_s: int = 60
    env: Optional[Dict[str, str]] = None
    cwd: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)
def _pyc(code: str) -> List[str]:
    return ["python", "-c", code]


def _sh(cmd: str) -> List[str]:
    return ["sh", "-lc", cmd]
def minimal_probes(log_dir: str = CONTAINER_LOG_DIR) -> List[ProbeCommand]:
    """Return ordered probe commands from cheapest to heaviest.

    Each probe should attempt to write at least one artifact into log_dir.
    """
    ld = shlex.quote(log_dir)

    # Probe 1: pure python execution + log write (fastest, no deps)
    py_write = (
        "import os,sys,time,json,platform; "
        f"ld={ld!s}; "
        "os.makedirs(ld, exist_ok=True); "
        "p=os.path.join(ld,'probe_python.json'); "
        "d={'ts':time.time(),'argv':sys.argv,'exe':sys.executable,"
        "'py':sys.version,'platform':platform.platform(),"
        "'cwd':os.getcwd(),'uid':getattr(os,'getuid',lambda:None)(),"
        "'gid':getattr(os,'getgid',lambda:None)(),"
        "'env_keys':sorted(list(os.environ.keys()))[:50]}; "
        "open(p,'w',encoding='utf-8').write(json.dumps(d,sort_keys=True,indent=2)+'\n'); "
        "print('WROTE',p)"
    )

    # Probe 2: pytest single-file minimal test created in /tmp (avoids discovery)
    pytest_one = (
        "set -eu; "
        f"mkdir -p {ld}; "
        "cat >/tmp/test_minimal_probe.py <<'PY'
"
        "def test_minimal_probe():
"
        "    assert 1 + 1 == 2
"
        "PY
"
        f"python -c "import pathlib; p=pathlib.Path({ld!s})/'probe_pytest_started.txt'; "
        "p.write_text('started\n',encoding='utf-8')"; "
        "pytest -q /tmp/test_minimal_probe.py -s; "
        f"python -c "import pathlib; p=pathlib.Path({ld!s})/'probe_pytest_done.txt'; "
        "p.write_text('done\n',encoding='utf-8')""
    )

    # Probe 3: unittest single-file minimal test created in /tmp (no pytest dependency)
    unittest_one = (
        "set -eu; "
        f"mkdir -p {ld}; "
        "cat >/tmp/test_minimal_unittest_probe.py <<'PY'
"
        "import unittest
"
        "class T(unittest.TestCase):
"
        "    def test_ok(self):
"
        "        self.assertEqual(2, 1+1)
"
        "if __name__=='__main__':
"
        "    unittest.main(verbosity=2)
"
        "PY
"
        f"python -c "import pathlib; p=pathlib.Path({ld!s})/'probe_unittest_started.txt'; "
        "p.write_text('started\n',encoding='utf-8')"; "
        "python /tmp/test_minimal_unittest_probe.py; "
        f"python -c "import pathlib; p=pathlib.Path({ld!s})/'probe_unittest_done.txt'; "
        "p.write_text('done\n',encoding='utf-8')""
    )

    return [
        ProbeCommand(name="python_exec_and_log_write", argv=_pyc(py_write), timeout_s=30),
        ProbeCommand(name="pytest_single_test_file", argv=_sh(pytest_one), timeout_s=120),
        ProbeCommand(name="unittest_single_test_file", argv=_sh(unittest_one), timeout_s=120),
    ]
def minimal_probe_plan_json(log_dir: str = CONTAINER_LOG_DIR) -> str:
    """Convenience for dumping the probe plan (stable ordering) as JSON."""
    return json.dumps([asdict(p) for p in minimal_probes(log_dir)], indent=2, sort_keys=True) + "\n"


def recommended_container_mounts(host_outputs_dir: str) -> Dict[str, str]:
    """Return a minimal set of mounts expected by probes.

    host_outputs_dir should map to /outputs in the container.
    """
    return {os.path.abspath(host_outputs_dir): "/outputs"}

from pathlib import Path
import sys
import json
import subprocess
import selectors
from datetime import datetime, timezone
from typing import Iterable, Optional, Union, Dict, Any
def utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
def sanitize_step_name(name: str) -> str:
    return "".join(c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in name).strip("._") or "step" 
class StepLogger:
    def __init__(self, build_dir: Union[str, Path], step: str, also_jsonl: bool = True):
        self.build_dir = Path(build_dir)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.step = sanitize_step_name(step)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_path = self.build_dir / f"{self.step}_{stamp}.log"
        self.jsonl_path = self.build_dir / f"{self.step}_{stamp}.jsonl"
        self._log_f = self.log_path.open("a", encoding="utf-8")
        self._jsonl_f = self.jsonl_path.open("a", encoding="utf-8") if also_jsonl else None

    def close(self) -> None:
        try:
            self._log_f.flush()
            self._log_f.close()
        finally:
            if self._jsonl_f:
                self._jsonl_f.flush()
                self._jsonl_f.close()

    def _write_jsonl(self, rec: Dict[str, Any]) -> None:
        if not self._jsonl_f:
            return
        self._jsonl_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._jsonl_f.flush()

    def log(self, msg: str, level: str = "INFO", data: Optional[Dict[str, Any]] = None) -> None:
        ts = utc_ts()
        prefix = f"[{ts}] [{self.step}] [{level}] "
        line = prefix + msg.rstrip("\n") + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()
        self._log_f.write(line)
        self._log_f.flush()
        rec = {"ts": ts, "step": self.step, "level": level, "msg": msg}
        if data:
            rec["data"] = data
        self._write_jsonl(rec)

    def tee_subprocess(
        self,
        args: Union[str, Iterable[str]],
        cwd: Optional[Union[str, Path]] = None,
        env: Optional[Dict[str, str]] = None,
        shell: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        ts0 = utc_ts()
        self.log("subprocess:start", data={"args": args, "cwd": str(cwd) if cwd else None, "shell": shell})
        p = subprocess.Popen(
            args,
            cwd=str(cwd) if cwd else None,
            env=env,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        sel = selectors.DefaultSelector()
        assert p.stdout and p.stderr
        sel.register(p.stdout, selectors.EVENT_READ, data="stdout")
        sel.register(p.stderr, selectors.EVENT_READ, data="stderr")

        out_lines, err_lines = [], []
        while sel.get_map():
            for key, _ in sel.select():
                stream = key.data
                f = key.fileobj
                line = f.readline()
                if line == "":
                    sel.unregister(f)
                    continue
                ts = utc_ts()
                tag = "OUT" if stream == "stdout" else "ERR"
                prefix = f"[{ts}] [{self.step}] [{tag}] "
                text = prefix + line.rstrip("\n") + "\n"
                (sys.stdout if stream == "stdout" else sys.stderr).write(text)
                (sys.stdout if stream == "stdout" else sys.stderr).flush()
                self._log_f.write(text)
                self._log_f.flush()
                self._write_jsonl({"ts": ts, "step": self.step, "stream": stream, "line": line.rstrip("\n")})
                (out_lines if stream == "stdout" else err_lines).append(line)

        rc = p.wait()
        ts1 = utc_ts()
        self.log(
            "subprocess:end",
            level=("INFO" if rc == 0 else "ERROR"),
            data={"returncode": rc, "started": ts0, "ended": ts1},
        )

        cp = subprocess.CompletedProcess(args=args, returncode=rc, stdout="".join(out_lines), stderr="".join(err_lines))
        if check and rc != 0:
            raise subprocess.CalledProcessError(rc, args, output=cp.stdout, stderr=cp.stderr)
        return cp

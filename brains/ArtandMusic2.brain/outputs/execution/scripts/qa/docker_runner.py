from __future__ import annotations
import json, os, shlex, subprocess, time, threading
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple, Union

ROOT = Path('/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution')
LOG_ROOT = ROOT / 'outputs' / 'qa' / 'logs'
LOG_ROOT.mkdir(parents=True, exist_ok=True)

def _now_ms() -> int:
    return int(time.time() * 1000)

def _jwrite(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')

def _append(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a', encoding='utf-8', errors='replace') as f:
        f.write(s)

def _run(cmd: Sequence[str], timeout: Optional[float]=None, check: bool=False, env: Optional[Dict[str,str]]=None) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout, check=check, env=env)

def _safe_name(s: str) -> str:
    keep = []
    for ch in s:
        if ch.isalnum() or ch in ('-','_','.'): keep.append(ch)
        else: keep.append('_')
    out = ''.join(keep).strip('_')
    return out[:80] if out else 'run'

@dataclass
class DockerResources:
    memory: Optional[str]=None
    cpus: Optional[str]=None
    pids_limit: Optional[int]=None
    ulimit_nofile: Optional[int]=None

@dataclass
class RunResult:
    ok: bool
    container_id: str
    exit_code: Optional[int]
    timed_out: bool
    start_ms: int
    end_ms: int
    artifacts_dir: str
    error: Optional[str]=None
class DockerRunner:
    """Robust docker wrapper for diagnostic runs: captures logs, inspect/state, events, exit code, and timeouts."""

    def __init__(self, logs_root: Path = LOG_ROOT):
        self.logs_root = Path(logs_root)
        self.logs_root.mkdir(parents=True, exist_ok=True)

    def docker_version(self) -> Dict[str,str]:
        res = _run(['docker','version','--format','{{json .}}'])
        if res.returncode == 0 and res.stdout.strip():
            try: return json.loads(res.stdout)
            except Exception: pass
        return {'rc': str(res.returncode), 'stdout': res.stdout, 'stderr': res.stderr}

    def _docker(self, args: Sequence[str], timeout: Optional[float]=None) -> subprocess.CompletedProcess:
        return _run(['docker', *args], timeout=timeout)

    def _spawn_events(self, cid: str, out_path: Path, stop_evt: threading.Event) -> threading.Thread:
        def _t():
            cmd = ['docker','events','--filter',f'container={cid}','--format','{{json .}}']
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            while not stop_evt.is_set():
                line = p.stdout.readline() if p.stdout else ''
                if line:
                    _append(out_path, line if line.endswith('\n') else line + '\n')
                else:
                    if p.poll() is not None: break
                    time.sleep(0.05)
            try:
                if p.poll() is None: p.terminate()
            except Exception:
                pass
            try:
                err = (p.stderr.read() if p.stderr else '') if p.poll() is not None else ''
                if err: _append(out_path.with_suffix('.stderr.txt'), err)
            except Exception:
                pass
        th = threading.Thread(target=_t, daemon=True)
        th.start()
        return th

    def _spawn_logs(self, cid: str, out_path: Path, stop_evt: threading.Event) -> threading.Thread:
        def _t():
            cmd = ['docker','logs','-f',cid]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            while not stop_evt.is_set():
                line = p.stdout.readline() if p.stdout else ''
                if line:
                    _append(out_path, line if line.endswith('\n') else line + '\n')
                else:
                    if p.poll() is not None: break
                    time.sleep(0.05)
            try:
                if p.poll() is None: p.terminate()
            except Exception:
                pass
            try:
                err = (p.stderr.read() if p.stderr else '') if p.poll() is not None else ''
                if err: _append(out_path.with_suffix('.stderr.txt'), err)
            except Exception:
                pass
        th = threading.Thread(target=_t, daemon=True)
        th.start()
        return th

    def _inspect(self, cid: str) -> Dict:
        res = self._docker(['inspect', cid])
        if res.returncode == 0 and res.stdout.strip():
            try:
                arr = json.loads(res.stdout)
                return arr[0] if isinstance(arr, list) and arr else arr
            except Exception:
                return {'parse_error': True, 'stdout': res.stdout, 'stderr': res.stderr, 'rc': res.returncode}
        return {'rc': res.returncode, 'stdout': res.stdout, 'stderr': res.stderr}

    def _state(self, cid: str) -> Dict:
        res = self._docker(['inspect','--format','{{json .State}}',cid])
        if res.returncode == 0 and res.stdout.strip():
            try: return json.loads(res.stdout)
            except Exception: return {'raw': res.stdout}
        return {'rc': res.returncode, 'stdout': res.stdout, 'stderr': res.stderr}

    def run(self,
            image: str,
            command: Union[str, Sequence[str]],
            *,
            name: Optional[str]=None,
            workdir: Optional[str]=None,
            mounts: Optional[Sequence[Tuple[str,str,bool]]]=None,
            env: Optional[Dict[str,str]]=None,
            resources: Optional[DockerResources]=None,
            timeout_s: float=600.0,
            pull: bool=False,
            labels: Optional[Dict[str,str]]=None) -> RunResult:
        run_id = f"{_safe_name(name or 'diagnostic')}-{_now_ms()}"
        adir = self.logs_root / run_id
        adir.mkdir(parents=True, exist_ok=True)

        meta = {'image': image, 'command': command, 'name': name, 'workdir': workdir,
                'mounts': mounts or [], 'env': env or {}, 'resources': asdict(resources or DockerResources()),
                'timeout_s': timeout_s, 'pull': pull, 'labels': labels or {}, 'docker_version': self.docker_version()}
        _jwrite(adir / 'request.json', meta)

        if pull:
            pr = self._docker(['pull', image], timeout=max(120.0, timeout_s))
            _jwrite(adir / 'pull.json', {'rc': pr.returncode, 'stdout': pr.stdout, 'stderr': pr.stderr})

        args: List[str] = ['create', '--init', '--rm']
        if workdir: args += ['-w', workdir]
        if env:
            for k,v in env.items(): args += ['-e', f'{k}={v}']
        if mounts:
            for host, cont, ro in mounts:
                hostp = str(Path(host).resolve())
                spec = f'type=bind,src={hostp},dst={cont}'
                if ro: spec += ',readonly'
                args += ['--mount', spec]
        if labels:
            for k,v in labels.items(): args += ['--label', f'{k}={v}']
        r = resources or DockerResources()
        if r.memory: args += ['--memory', r.memory]
        if r.cpus: args += ['--cpus', r.cpus]
        if r.pids_limit is not None: args += ['--pids-limit', str(r.pids_limit)]
        if r.ulimit_nofile is not None: args += ['--ulimit', f'nofile={r.ulimit_nofile}:{r.ulimit_nofile}']
        args.append(image)
        if isinstance(command, str): args += shlex.split(command)
        else: args += list(command)

        c = self._docker(args)
        _jwrite(adir / 'create.json', {'cmd': ['docker', *args], 'rc': c.returncode, 'stdout': c.stdout, 'stderr': c.stderr})
        if c.returncode != 0 or not c.stdout.strip():
            res = RunResult(ok=False, container_id='', exit_code=None, timed_out=False,
                            start_ms=_now_ms(), end_ms=_now_ms(), artifacts_dir=str(adir),
                            error=f'create_failed rc={c.returncode}')
            _jwrite(adir / 'result.json', asdict(res))
            return res
        cid = c.stdout.strip().splitlines()[-1].strip()
        _jwrite(adir / 'inspect.create.json', self._inspect(cid))

        start_ms = _now_ms()
        sevt, slog = threading.Event(), threading.Event()
        events_th = self._spawn_events(cid, adir / 'events.jsonl', sevt)
        logs_th = self._spawn_logs(cid, adir / 'container.log', slog)

        s = self._docker(['start', cid])
        _jwrite(adir / 'start.json', {'rc': s.returncode, 'stdout': s.stdout, 'stderr': s.stderr})
        if s.returncode != 0:
            sevt.set(); slog.set()
            time.sleep(0.1)
            res = RunResult(ok=False, container_id=cid, exit_code=None, timed_out=False,
                            start_ms=start_ms, end_ms=_now_ms(), artifacts_dir=str(adir),
                            error=f'start_failed rc={s.returncode}')
            _jwrite(adir / 'inspect.start_failed.json', self._inspect(cid))
            _jwrite(adir / 'result.json', asdict(res))
            return res

        timed_out = False
        exit_code: Optional[int] = None
        deadline = time.time() + float(timeout_s)
        while True:
            st = self._state(cid)
            _jwrite(adir / 'state.last.json', st)
            if isinstance(st, dict) and st.get('Status') in ('exited','dead'):
                try: exit_code = int(st.get('ExitCode'))
                except Exception: exit_code = None
                break
            if time.time() > deadline:
                timed_out = True
                _jwrite(adir / 'timeout.json', {'at_ms': _now_ms(), 'timeout_s': timeout_s})
                self._docker(['kill', cid])
                time.sleep(0.2)
                st2 = self._state(cid)
                _jwrite(adir / 'state.after_kill.json', st2)
                try: exit_code = int(st2.get('ExitCode')) if isinstance(st2, dict) else None
                except Exception: exit_code = None
                break
            time.sleep(0.25)

        end_ms = _now_ms()
        sevt.set(); slog.set()
        for th in (events_th, logs_th):
            try: th.join(timeout=2.0)
            except Exception: pass

        _jwrite(adir / 'inspect.final.json', self._inspect(cid))
        w = self._docker(['wait', cid], timeout=5.0)
        _jwrite(adir / 'wait.json', {'rc': w.returncode, 'stdout': w.stdout, 'stderr': w.stderr})

        ok = (not timed_out) and (exit_code == 0)
        res = RunResult(ok=ok, container_id=cid, exit_code=exit_code, timed_out=timed_out,
                        start_ms=start_ms, end_ms=end_ms, artifacts_dir=str(adir),
                        error=None if ok else ('timeout' if timed_out else f'exit_code={exit_code}'))
        _jwrite(adir / 'result.json', asdict(res))
        return res

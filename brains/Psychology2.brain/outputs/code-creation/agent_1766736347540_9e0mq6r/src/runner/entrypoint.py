#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, time, uuid, shlex, subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve()
for _ in range(6):
    if (ROOT.parent / "runtime").exists():
        ROOT = ROOT.parent
        break
    ROOT = ROOT.parent
BASE = ROOT if (ROOT / "runtime").exists() else Path.cwd()
LOG_DIR = BASE / "runtime" / "_build" / "logs"

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def atomic_write(path: Path, data: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data, encoding="utf-8")
    tmp.replace(path)

def load_config(argv: list[str]) -> dict:
    cfg_path = None
    if len(argv) > 1 and argv[1].strip():
        cfg_path = Path(argv[1]).expanduser()
        if not cfg_path.is_absolute():
            cfg_path = (BASE / cfg_path).resolve()
    elif os.environ.get("RUNNER_CONFIG"):
        cfg_path = Path(os.environ["RUNNER_CONFIG"]).expanduser()
        if not cfg_path.is_absolute():
            cfg_path = (BASE / cfg_path).resolve()
    else:
        for cand in [BASE / "runtime" / "config.json", BASE / "config.json"]:
            if cand.exists():
                cfg_path = cand
                break
    if not cfg_path or not cfg_path.exists():
        raise SystemExit("Missing config: provide path arg, RUNNER_CONFIG, or runtime/config.json")
    return json.loads(cfg_path.read_text(encoding="utf-8"))

def cfg_command(cfg: dict) -> list[str]:
    cmd = cfg.get("command") or cfg.get("cmd")
    if cmd is None:
        raise SystemExit("Config missing 'command' (list or string).")
    if isinstance(cmd, list):
        return [str(x) for x in cmd]
    if isinstance(cmd, str):
        return shlex.split(cmd)
    raise SystemExit("Invalid 'command' type; must be list or string.")

def run_docker(cfg: dict, log_fp) -> dict:
    image = cfg.get("image") or cfg.get("docker_image")
    if not image:
        raise SystemExit("Config missing 'image'.")
    env = cfg.get("env") or {}
    workdir = cfg.get("workdir") or cfg.get("working_dir")
    mounts = cfg.get("mounts") or cfg.get("volumes") or []
    name = cfg.get("container_name") or f"run_{uuid.uuid4().hex[:12]}"
    cmd = cfg_command(cfg)

    def log(line: str) -> None:
        ts = utc_now()
        log_fp.write(f"[{ts}] {line.rstrip()}\n")
        log_fp.flush()

    docker = cfg.get("docker_bin") or "docker"
    create = [docker, "create", "--name", name]
    if workdir:
        create += ["-w", str(workdir)]
    for k, v in (env.items() if isinstance(env, dict) else []):
        create += ["-e", f"{k}={v}"]
    for m in mounts:
        if isinstance(m, str):
            create += ["-v", m]
        elif isinstance(m, dict):
            src = m.get("src") or m.get("source") or m.get("host")
            dst = m.get("dst") or m.get("target") or m.get("container")
            mode = m.get("mode")
            if src and dst:
                spec = f"{src}:{dst}" + (f":{mode}" if mode else "")
                create += ["-v", spec]
    create += [image] + cmd

    meta = {
        "container_name": name,
        "container_id": None,
        "container_lost": False,
        "container_lost_at": None,
        "docker_create_rc": None,
        "docker_start_rc": None,
        "docker_wait_rc": None,
        "exit_code": None,
        "error": None,
    }

    log(f"docker_create: {' '.join(shlex.quote(x) for x in create)}")
    p = subprocess.run(create, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    meta["docker_create_rc"] = p.returncode
    if p.stdout.strip():
        meta["container_id"] = p.stdout.strip().splitlines()[-1]
    if p.returncode != 0:
        meta["error"] = (p.stderr or p.stdout or "").strip()
        log(f"docker_create_failed rc={p.returncode} err={meta['error']}")
        return meta

    cid = meta["container_id"] or name
    log(f"container_created id={cid}")

    logs_cmd = [docker, "logs", "-f", cid]
    start_cmd = [docker, "start", cid]
    wait_cmd = [docker, "wait", cid]

    log(f"docker_logs: {' '.join(shlex.quote(x) for x in logs_cmd)}")
    log_proc = subprocess.Popen(logs_cmd, stdout=log_fp, stderr=log_fp, text=True)

    log(f"docker_start: {' '.join(shlex.quote(x) for x in start_cmd)}")
    sp = subprocess.run(start_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    meta["docker_start_rc"] = sp.returncode
    if sp.returncode != 0:
        meta["error"] = (sp.stderr or sp.stdout or "").strip()
        log(f"docker_start_failed rc={sp.returncode} err={meta['error']}")
        try: log_proc.terminate()
        except Exception: pass
        return meta

    log(f"docker_wait: {' '.join(shlex.quote(x) for x in wait_cmd)}")
    wp = subprocess.run(wait_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    meta["docker_wait_rc"] = wp.returncode

    if wp.returncode == 0 and wp.stdout.strip().isdigit():
        meta["exit_code"] = int(wp.stdout.strip())
    else:
        err = (wp.stderr or wp.stdout or "").strip()
        meta["error"] = err or meta["error"]
        meta["container_lost"] = True
        meta["container_lost_at"] = utc_now()
        log(f"container_lost_detected err={err}")

    for _ in range(50):
        if log_proc.poll() is not None:
            break
        time.sleep(0.1)
    if log_proc.poll() is None:
        try: log_proc.terminate()
        except Exception: pass

    rm_cmd = [docker, "rm", "-f", cid]
    subprocess.run(rm_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    return meta

def main(argv: list[str]) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run_id = os.environ.get("RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    log_path = LOG_DIR / "run.log"
    env_path = LOG_DIR / "env_snapshot.json"
    cfg_path = LOG_DIR / "config.json"
    summary_path = LOG_DIR / "run_summary.json"

    start = utc_now()
    cfg = load_config(argv)
    atomic_write(cfg_path, json.dumps(cfg, indent=2, sort_keys=True) + "\n")
    atomic_write(env_path, json.dumps(dict(os.environ), indent=2, sort_keys=True) + "\n")

    meta = {}
    try:
        with log_path.open("a", encoding="utf-8") as log_fp:
            log_fp.write(f"[{utc_now()}] runner_start run_id={run_id} base={BASE}\n")
            log_fp.flush()
            meta = run_docker(cfg, log_fp)
            log_fp.write(f"[{utc_now()}] runner_end\n")
            log_fp.flush()
    except Exception as e:
        meta = meta or {}
        meta.setdefault("error", f"{type(e).__name__}: {e}")
        meta.setdefault("exit_code", None)

    end = utc_now()
    summary = {
        "schema_version": 1,
        "run_id": run_id,
        "start_time_utc": start,
        "end_time_utc": end,
        "base_dir": str(BASE),
        "log_dir": str(LOG_DIR),
        "artifacts": {
            "run_log": str(log_path),
            "env_snapshot": str(env_path),
            "config": str(cfg_path),
        },
        "docker": {
            "container_name": meta.get("container_name"),
            "container_id": meta.get("container_id"),
            "exit_code": meta.get("exit_code"),
            "container_lost": bool(meta.get("container_lost")),
            "container_lost_at_utc": meta.get("container_lost_at"),
            "docker_create_rc": meta.get("docker_create_rc"),
            "docker_start_rc": meta.get("docker_start_rc"),
            "docker_wait_rc": meta.get("docker_wait_rc"),
            "error": meta.get("error"),
        },
        "status": ("container_lost" if meta.get("container_lost") else ("ok" if meta.get("exit_code") == 0 else "error")),
    }
    atomic_write(summary_path, json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return int(meta.get("exit_code") or (1 if meta.get("error") or meta.get("container_lost") else 0))

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

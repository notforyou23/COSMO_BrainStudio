#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

EXIT_PASS, EXIT_FAIL, EXIT_ERROR = 0, 2, 3

def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def _atomic_write_json(path: Path, payload: dict) -> None:
    _ensure_dir(path.parent)
    data = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass

def _write_log(path: Path, text: str) -> None:
    _ensure_dir(path.parent)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text.rstrip("\n") + "\n")

def _docker_available(log: list[str]) -> bool:
    try:
        p = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
        log.append(f"$ docker info -> {p.returncode}")
        if p.stdout:
            log.append(p.stdout.strip())
        if p.stderr:
            log.append(p.stderr.strip())
        return p.returncode == 0
    except FileNotFoundError:
        log.append("docker executable not found")
        return False
    except Exception as e:
        log.append(f"docker availability check error: {type(e).__name__}: {e}")
        return False

def _run_docker(root: Path, log: list[str]) -> tuple[bool, int]:
    cmd = os.environ.get("QA_DOCKER_CMD", "").strip()
    if cmd:
        argv = cmd.split()
    else:
        image = os.environ.get("QA_DOCKER_IMAGE", "").strip()
        if not image:
            log.append("No QA_DOCKER_CMD/QA_DOCKER_IMAGE configured; skipping docker mode.")
            return False, EXIT_ERROR
        argv = ["docker","run","--rm","-v",f"{root}:/work","-w","/work",image,"python","scripts/qa_run.py","--no-docker"]
    log.append("$ " + " ".join(argv))
    try:
        p = subprocess.run(argv, cwd=str(root), capture_output=True, text=True)
        if p.stdout:
            log.append(p.stdout.rstrip())
        if p.stderr:
            log.append(p.stderr.rstrip())
        return True, (EXIT_PASS if p.returncode == 0 else EXIT_FAIL)
    except FileNotFoundError:
        log.append("docker executable not found during run")
        return False, EXIT_ERROR
    except Exception as e:
        log.append(f"docker run error: {type(e).__name__}: {e}")
        return False, EXIT_ERROR

def _load_json(path: Path) -> tuple[bool, object | None, str | None]:
    try:
        return True, json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}"

def _schema_for(json_path: Path, root: Path) -> Path | None:
    rel = None
    try:
        rel = json_path.relative_to(root)
    except Exception:
        rel = json_path.name
    candidates = []
    if isinstance(rel, Path):
        candidates.append(root / "schemas" / rel.with_suffix(rel.suffix + ".schema.json"))
        candidates.append(json_path.with_suffix(json_path.suffix + ".schema.json"))
    else:
        candidates.append(root / "schemas" / (str(rel) + ".schema.json"))
    for c in candidates:
        if c.exists():
            return c
    return None

def _validate_schema(instance: object, schema_path: Path) -> tuple[bool, str | None]:
    ok, schema, err = _load_json(schema_path)
    if not ok:
        return False, f"schema load failed: {err}"
    try:
        import jsonschema  # pure-python package in most envs
        jsonschema.validate(instance=instance, schema=schema)
        return True, None
    except ImportError:
        return False, "jsonschema not installed"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

def _linkcheck_file(md_path: Path, root: Path) -> list[str]:
    txt = md_path.read_text(encoding="utf-8", errors="ignore")
    bad = []
    for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", txt):
        url = m.group(1).strip()
        if not url or url.startswith(("#","http://","https://","mailto:")):
            continue
        url = url.split("#", 1)[0]
        if not url:
            continue
        target = (md_path.parent / url).resolve()
        if not str(target).startswith(str(root.resolve())):
            continue
        if not target.exists():
            bad.append(url)
    return bad

def _failsafe_checks(root: Path, do_linkcheck: bool, log: list[str]) -> tuple[list[dict], int]:
    outputs = root / "outputs"
    checks = []
    if not outputs.exists():
        checks.append({"name":"outputs_dir","status":"fail","details":f"missing: {outputs}"})
        return checks, EXIT_FAIL
    checks.append({"name":"outputs_dir","status":"pass","details":str(outputs)})
    json_files = sorted([p for p in outputs.rglob("*.json") if p.is_file()])
    if not json_files:
        checks.append({"name":"json_presence","status":"fail","details":"no JSON files found under outputs/"})
        code = EXIT_FAIL
    else:
        checks.append({"name":"json_presence","status":"pass","details":f"{len(json_files)} JSON files"})
        code = EXIT_PASS
    for p in json_files:
        ok, obj, err = _load_json(p)
        checks.append({"name":"json_parse","path":str(p.relative_to(root)),"status":"pass" if ok else "fail","details":err or "ok"})
        if not ok:
            code = EXIT_FAIL
            continue
        sp = _schema_for(p, root)
        if sp and sp.exists():
            vok, verr = _validate_schema(obj, sp)
            checks.append({"name":"json_schema","path":str(p.relative_to(root)),"schema":str(sp.relative_to(root)),"status":"pass" if vok else "fail","details":verr or "ok"})
            if not vok:
                code = EXIT_FAIL
        else:
            checks.append({"name":"json_schema","path":str(p.relative_to(root)),"status":"skip","details":"no schema found"})
    if do_linkcheck:
        md_files = sorted([p for p in root.rglob("*.md") if p.is_file() and "outputs" not in p.parts])
        broken = []
        for md in md_files:
            for b in _linkcheck_file(md, root):
                broken.append(f"{md.relative_to(root)} -> {b}")
        if broken:
            checks.append({"name":"linkcheck","status":"fail","details":broken[:200]})
            code = EXIT_FAIL
        else:
            checks.append({"name":"linkcheck","status":"pass","details":"no broken relative links detected"})
    else:
        checks.append({"name":"linkcheck","status":"skip","details":"disabled"})
    return checks, code

def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Canonical QA runner with deterministic failsafe mode.")
    ap.add_argument("--no-docker", action="store_true", help="Force failsafe no-container mode.")
    ap.add_argument("--linkcheck", action="store_true", help="Enable lightweight linkcheck of markdown relative links.")
    args = ap.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    qa_dir = root / "outputs" / "qa"
    report_path = qa_dir / "QA_REPORT.json"
    log_path = qa_dir / "qa_run.log"
    run_log, mode = [], "failsafe"
    started = _now()
    exit_code = EXIT_ERROR
    checks = []
    try:
        if not args.no_docker:
            if _docker_available(run_log):
                ran, code = _run_docker(root, run_log)
                if ran and code == EXIT_PASS and report_path.exists():
                    mode, exit_code = "docker", EXIT_PASS
                    return EXIT_PASS
                if ran and code != EXIT_ERROR:
                    mode, exit_code = "docker", code
                else:
                    run_log.append("Docker unavailable/unreliable; falling back to failsafe checks.")
            else:
                run_log.append("Docker not available; falling back to failsafe checks.")
        checks, exit_code = _failsafe_checks(root, args.linkcheck, run_log)
        mode = "failsafe"
        return exit_code
    except Exception as e:
        run_log.append(f"runner error: {type(e).__name__}: {e}")
        exit_code = EXIT_ERROR
        return EXIT_ERROR
    finally:
        finished = _now()
        summary = {
            "mode": mode,
            "started_at": started,
            "finished_at": finished,
            "exit_code": int(exit_code),
            "checks": checks,
        }
        _atomic_write_json(report_path, summary)
        _write_log(log_path, f"[{finished}] mode={mode} exit_code={exit_code}")
        if run_log:
            _write_log(log_path, "\n".join(run_log))

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

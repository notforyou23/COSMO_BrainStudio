#!/usr/bin/env python3
from __future__ import annotations
import json, os, sys, time, traceback, logging
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD_DIR = HERE / "runtime" / "_build"
LOG_DIR = BUILD_DIR / "logs"
LOG_PATH = LOG_DIR / "run.log"
MANIFEST_PATH = BUILD_DIR / "manifest.json"

def _setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("run_pipeline")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s", "%Y-%m-%dT%H:%M:%S")
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh); logger.addHandler(sh)
    logger.propagate = False
    logger.info("log_path=%s", str(LOG_PATH))
    return logger

def _jsonable(o):
    try:
        json.dumps(o); return o
    except Exception:
        return str(o)

def _write_manifest(manifest: dict):
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(MANIFEST_PATH)

def _find_first(names: list[str]) -> Path | None:
    for name in names:
        for p in HERE.rglob(name):
            if p.is_file() and BUILD_DIR not in p.parents:
                return p
    return None

def stage_preflight(logger: logging.Logger) -> dict:
    if sys.version_info < (3, 9):
        raise RuntimeError(f"Python>=3.9 required, got {sys.version.split()[0]}")
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    test = BUILD_DIR / ".write_test"
    test.write_text("ok", encoding="utf-8")
    test.unlink(missing_ok=True)
    logger.info("preflight_ok python=%s cwd=%s", sys.version.split()[0], os.getcwd())
    return {"python": sys.version.split()[0], "cwd": os.getcwd(), "here": str(HERE)}

def stage_artifact_gate(logger: logging.Logger) -> dict:
    roots = [HERE, HERE / "runtime", HERE / "outputs", HERE / "artifacts"]
    exts = {".json", ".csv", ".tsv", ".txt", ".md"}
    found = []
    for r in roots:
        if r.exists():
            for p in r.rglob("*"):
                if p.is_file() and p.suffix.lower() in exts and BUILD_DIR not in p.parents:
                    found.append(p)
                    if len(found) >= 25:
                        break
        if len(found) >= 25:
            break
    if not found:
        raise RuntimeError("artifact_gate_failed: no artifact-like files found")
    sizes = [p.stat().st_size for p in found]
    logger.info("artifact_gate_ok files_sampled=%d", len(found))
    return {"sampled_files": [str(p.relative_to(HERE)) for p in found[:10]],
            "sampled_count": len(found),
            "sampled_total_bytes": int(sum(sizes))}

def stage_taxonomy_validator(logger: logging.Logger) -> dict:
    tax = _find_first(["taxonomy.json", "taxonomy.yaml", "taxonomy.yml"])
    if not tax:
        logger.info("taxonomy_validator_skipped no taxonomy file found")
        return {"status": "skipped"}
    if tax.suffix.lower() == ".json":
        data = json.loads(tax.read_text(encoding="utf-8"))
        if not isinstance(data, (dict, list)):
            raise RuntimeError("taxonomy_invalid: root must be object or array")
        if isinstance(data, dict) and not data:
            raise RuntimeError("taxonomy_invalid: empty object")
    else:
        txt = tax.read_text(encoding="utf-8").strip()
        if not txt or txt.startswith("#"):
            raise RuntimeError("taxonomy_invalid: empty/invalid yaml (no parser available)")
    logger.info("taxonomy_validator_ok path=%s", str(tax))
    return {"status": "ok", "path": str(tax.relative_to(HERE)), "bytes": tax.stat().st_size}

def stage_toy_meta_analysis(logger: logging.Logger) -> dict:
    exts = {}
    total_bytes = 0
    total_files = 0
    for p in HERE.rglob("*"):
        if p.is_file() and BUILD_DIR not in p.parents:
            total_files += 1
            total_bytes += p.stat().st_size
            k = p.suffix.lower() or "<noext>"
            exts[k] = exts.get(k, 0) + 1
    top = sorted(exts.items(), key=lambda kv: (-kv[1], kv[0]))[:15]
    logger.info("meta_analysis_ok total_files=%d total_bytes=%d", total_files, total_bytes)
    return {"total_files": total_files, "total_bytes": int(total_bytes), "top_extensions": top}

def run() -> int:
    logger = _setup_logging()
    started = time.time()
    manifest = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "build_dir": str(BUILD_DIR), "log_path": str(LOG_PATH),
                "stages": [], "success": False}
    rc = 0
    try:
        for name, fn in [
            ("preflight", stage_preflight),
            ("artifact_gate", stage_artifact_gate),
            ("taxonomy_validator", stage_taxonomy_validator),
            ("toy_meta_analysis", stage_toy_meta_analysis),
        ]:
            t0 = time.time()
            logger.info("stage_start %s", name)
            out = fn(logger)
            manifest["stages"].append({"name": name, "ok": True, "seconds": round(time.time()-t0, 6), "output": _jsonable(out)})
            logger.info("stage_ok %s", name)
        manifest["success"] = True
        return 0
    except Exception as e:
        rc = 1
        tb = traceback.format_exc()
        logger.error("pipeline_failed %s", str(e))
        logger.error(tb)
        manifest["stages"].append({"name": "failure", "ok": False, "error": str(e), "traceback": tb})
        return 1
    finally:
        manifest["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        manifest["elapsed_seconds"] = round(time.time() - started, 6)
        try:
            _write_manifest(manifest)
            logger.info("manifest_written path=%s", str(MANIFEST_PATH))
        except Exception:
            print("ERROR: failed to write manifest", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)

if __name__ == "__main__":
    sys.exit(run())

#!/usr/bin/env python3
from __future__ import annotations
import argparse, contextlib, datetime as dt, json, os, sys, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "outputs"

def _ts() -> str:
    return dt.datetime.utcnow().replace(microsecond=0).isoformat().replace(":", "").replace("-", "") + "Z"

def _w(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    os.replace(tmp, path)

@contextlib.contextmanager
def _capture(log_path: Path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    f = open(log_path, "a", encoding="utf-8")
    class Tee:
        def __init__(self, a, b): self.a, self.b = a, b
        def write(self, s): self.a.write(s); self.b.write(s); self.a.flush(); self.b.flush()
        def flush(self): self.a.flush(); self.b.flush()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = Tee(old_out, f), Tee(old_err, f)
    try:
        yield
    finally:
        sys.stdout, sys.stderr = old_out, old_err
        f.close()

def _seed_bib() -> str:
    return (
'@article{knuth1984literate,\n'
'  title={Literate programming},\n'
'  author={Knuth, Donald E.},\n'
'  journal={The Computer Journal},\n'
'  volume={27},\n'
'  number={2},\n'
'  pages={97--111},\n'
'  year={1984},\n'
'  publisher={Oxford University Press}\n'
'}\n\n'
'@misc{semver2013,\n'
'  title={Semantic Versioning 2.0.0},\n'
'  author={{Tom Preston-Werner}},\n'
'  year={2013},\n'
'  howpublished={https://semver.org/},\n'
'  note={Accessed: 2025-12-24}\n'
'}\n'
    )

def _bib_keys(bib_text: str) -> list[str]:
    keys = []
    for line in bib_text.splitlines():
        line = line.strip()
        if line.startswith("@") and "{" in line and "," in line:
            keys.append(line.split("{", 1)[1].split(",", 1)[0].strip())
    return [k for k in keys if k]

def run(out_dir: Path) -> dict:
    stamp = _ts()
    run_dir = out_dir / "runs" / stamp
    log_path = run_dir / "run.log"
    artifacts = {}
    with _capture(log_path):
        print(f"pipeline_start ts={stamp} out_dir={out_dir} run_dir={run_dir}")
        (run_dir / "results").mkdir(parents=True, exist_ok=True)

        # (1) captured logs/results
        results = {
            "project": "generated_script_1766550289431",
            "stage": "Stage 1",
            "mode": "create",
            "timestamp_utc": stamp,
            "cwd": str(Path.cwd()),
            "python": sys.version.split()[0],
        }
        _w(run_dir / "results" / "results.json", json.dumps(results, indent=2, sort_keys=True))
        artifacts["results_json"] = str((run_dir / "results" / "results.json").relative_to(out_dir))

        # (2) roadmap
        roadmap = (
            "# Roadmap\n\n"
            "Immediate milestone: **outputs-first**\n\n"
            "## Stage 1 (now)\n"
            "- Runnable pipeline CLI producing captured logs/results\n"
            "- Roadmap artifact\n"
            "- Bibliography subsystem w/ seed `.bib` + summary\n"
            "- Coverage matrix artifact\n"
            "- Checklist in `outputs/index.md`\n\n"
            "## Stage 2 (next)\n"
            "- Modularize into `src/pipeline/*` modules\n"
            "- Add configuration + reproducible paths + atomic writes everywhere\n"
            "- CI/CD integration (lint, format, tests)\n\n"
            "## Stage 3\n"
            "- Expand bibliography validation/normalization\n"
            "- Add richer research summarization + provenance\n"
            "- Extend coverage matrix to trace requirements -> artifacts -> evidence\n"
        )
        _w(run_dir / "roadmap.md", roadmap)
        artifacts["roadmap_md"] = str((run_dir / "roadmap.md").relative_to(out_dir))

        # (3) bibliography system + seed .bib + summary
        bib_dir = out_dir / "bibliography"
        bib_path = bib_dir / "references.bib"
        if not bib_path.exists():
            _w(bib_path, _seed_bib())
        else:
            _w(bib_path, bib_path.read_text(encoding="utf-8"))
        bib_text = bib_path.read_text(encoding="utf-8")
        keys = _bib_keys(bib_text)
        bib_summary = (
            "# Bibliography Summary\n\n"
            f"- Path: `{bib_path.relative_to(out_dir)}`\n"
            f"- Entry count (approx): {len(keys)}\n"
            f"- Keys: {', '.join(keys) if keys else '(none detected)'}\n"
        )
        _w(run_dir / "bibliography_summary.md", bib_summary)
        artifacts["references_bib"] = str(bib_path.relative_to(out_dir))
        artifacts["bibliography_summary_md"] = str((run_dir / "bibliography_summary.md").relative_to(out_dir))

        # (4) coverage matrix
        cov = (
            "# Coverage Matrix\n\n"
            "| Requirement | Artifact(s) | Evidence |\n"
            "|---|---|---|\n"
            f"| outputs-first runnable pipeline | `{artifacts['results_json']}`, `runs/{stamp}/run.log` | Run directory created w/ logs + results JSON |\n"
            f"| roadmap artifact | `{artifacts['roadmap_md']}` | Roadmap markdown written |\n"
            f"| bibliography system + seed .bib | `{artifacts['references_bib']}`, `{artifacts['bibliography_summary_md']}` | Seed `.bib` ensured and summary generated |\n"
            f"| coverage matrix | `runs/{stamp}/coverage_matrix.md` | This matrix written |\n"
            "| ci cd | `outputs/index.md` | Checklist includes CI/CD next steps |\n"
        )
        _w(run_dir / "coverage_matrix.md", cov)
        artifacts["coverage_matrix_md"] = str((run_dir / "coverage_matrix.md").relative_to(out_dir))

        # outputs/index.md checklist
        index = (
            "# Outputs Index\n\n"
            "## Checklist (outputs-first)\n"
            f"- [x] Captured logs/results: `runs/{stamp}/run.log`, `{artifacts['results_json']}`\n"
            f"- [x] Roadmap: `{artifacts['roadmap_md']}`\n"
            f"- [x] Bibliography seed: `{artifacts['references_bib']}`\n"
            f"- [x] Bibliography summary: `{artifacts['bibliography_summary_md']}`\n"
            f"- [x] Coverage matrix: `{artifacts['coverage_matrix_md']}`\n\n"
            "## Notes\n"
            "- This is Stage 1 of an outputs-first documentation-and-research pipeline.\n"
            "- CI/CD next: add lint/format/test jobs and artifact upload of `outputs/`.\n"
        )
        _w(out_dir / "index.md", index)
        artifacts["outputs_index_md"] = "index.md"

        print("pipeline_done artifacts=" + json.dumps(artifacts, sort_keys=True))
    return {"run_dir": str(run_dir), "artifacts": artifacts}

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Outputs-first documentation-and-research pipeline (Stage 1).")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="Outputs directory (default: ./outputs)")
    args = p.parse_args(argv)
    out_dir = Path(args.out).resolve()
    try:
        info = run(out_dir)
        print(json.dumps(info, indent=2, sort_keys=True))
        return 0
    except Exception:
        traceback.print_exc()
        return 2

if __name__ == "__main__":
    raise SystemExit(main())

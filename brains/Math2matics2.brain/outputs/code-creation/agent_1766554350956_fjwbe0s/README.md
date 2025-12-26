# generated_script_1766554289298

Minimal, runnable Python pipeline project.

## Roadmap
See: [Project Roadmap (v1)](roadmap_v1.md)

## Quickstart

### 1) Create and activate a virtual environment
- macOS/Linux:
  - `python -m venv .venv`
  - `source .venv/bin/activate`
- Windows (PowerShell):
  - `python -m venv .venv`
  - `.\.venv\Scripts\Activate.ps1`

### 2) Install dependencies
`pip install -r requirements.txt`

### 3) Run the pipeline
`python scripts/run_pipeline.py`

Outputs are written to `./outputs/`.

## CI
A GitHub Actions workflow (`.github/workflows/ci.yml`) runs `python scripts/run_pipeline.py` on a clean checkout after installing `requirements.txt`, then uploads `./outputs/` as build artifacts.

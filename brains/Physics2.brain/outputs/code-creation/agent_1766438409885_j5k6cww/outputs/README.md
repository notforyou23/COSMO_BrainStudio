# Benchmark reproduction (benchmark_case_001)

This repo ships a small, deterministic benchmark runner under `src/benchmark/`.
The CLI is invoked as a Python module, and (when running from source) requires
`PYTHONPATH=./src` so the `benchmark` package is importable.

## Reproduce benchmark_case_001

From the repo root:

```bash
export PYTHONPATH=./src
python -m benchmark.cli reproduce benchmark_case_001 --seed 0 --out outputs/benchmark_case_001.out.json
```

This writes `outputs/benchmark_case_001.out.json` as pretty-printed JSON.

## Verify against an expected JSON artifact

If you have an expected artifact (e.g. `outputs/benchmark_case_001.expected.json`),
you can reproduce *and* verify in one step:

```bash
export PYTHONPATH=./src
python -m benchmark.cli reproduce benchmark_case_001 --seed 0 \
  --out outputs/benchmark_case_001.out.json \
  --expected outputs/benchmark_case_001.expected.json
```

Numeric fields are compared with tolerances (defaults shown):

- `--rtol 1e-7`
- `--atol 1e-9`

You can also compare two JSON files directly:

```bash
export PYTHONPATH=./src
python -m benchmark.cli compare \
  --actual outputs/benchmark_case_001.out.json \
  --expected outputs/benchmark_case_001.expected.json
```

## Run tests (includes an end-to-end CLI check)

```bash
export PYTHONPATH=./src
pytest -q
```

## Notes for Windows shells

PowerShell:

```powershell
$env:PYTHONPATH = ".\src"
python -m benchmark.cli reproduce benchmark_case_001 --seed 0 --out outputs\benchmark_case_001.out.json
```

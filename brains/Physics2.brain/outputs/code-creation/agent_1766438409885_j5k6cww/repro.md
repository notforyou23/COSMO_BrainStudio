# Reproduction commands (pytest + benchmark_case_001)

All commands below were run from the repository root (`/mnt/data`) in the OpenAI Code Interpreter environment.

## Environment notes (for deterministic results)

- Python: `python -V`
- Set `PYTHONPATH=./src` (the project is run from source; no wheel install required).
- For extra determinism across runs, set:
  - `PYTHONHASHSEED=0` (stable hashing for any dict/set iteration that might leak into outputs)

## 1) Run the test suite

```bash
cd /mnt/data
export PYTHONPATH=./src
export PYTHONHASHSEED=0
pytest -q
```

## 2) Reproduce benchmark_case_001 output JSON

This generates `outputs/benchmark_case_001.out.json`:

```bash
cd /mnt/data
export PYTHONPATH=./src
export PYTHONHASHSEED=0
python -m benchmark.cli reproduce benchmark_case_001 --seed 0 --out outputs/benchmark_case_001.out.json
```

## 3) Reproduce *and* verify against the expected artifact

This reproduces the output and checks it matches `outputs/benchmark_case_001.expected.json`
within the CLI default tolerances (`rtol=1e-7`, `atol=1e-9`):

```bash
cd /mnt/data
export PYTHONPATH=./src
export PYTHONHASHSEED=0
python -m benchmark.cli reproduce benchmark_case_001 --seed 0 \
  --out outputs/benchmark_case_001.out.json \
  --expected outputs/benchmark_case_001.expected.json
```

## 4) Compare two JSON files directly (optional)

```bash
cd /mnt/data
export PYTHONPATH=./src
python -m benchmark.cli compare \
  --actual outputs/benchmark_case_001.out.json \
  --expected outputs/benchmark_case_001.expected.json
```

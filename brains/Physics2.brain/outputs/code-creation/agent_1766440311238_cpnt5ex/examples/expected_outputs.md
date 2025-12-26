# Expected outputs (examples)

This document provides concrete example invocations of the CLI along with **typical** stdout summaries and the **exact artifact filenames** the command is expected to create, to support reproducible Definition-of-Done checks.

Notes:

- Examples assume execution from the repository root.
- Paths are shown relative to the repo root.
- Stdout may include additional timing lines depending on platform; the key summary lines and filenames shown below must appear.

---

## 1) List available experiments

**Command**
```bash
python -m src.main list
```

**Expected stdout (summary)**
```text
AVAILABLE_EXPERIMENTS: 3
- logistic_map
- damped_oscillator
- symbolic_series
```

**Artifacts**
- None (this command only prints metadata).

---

## 2) Logistic map sweep (numerical)

Runs a classic nonlinear map sweep over parameters and saves a small CSV plus a PNG plot.

**Command**
```bash
python -m src.main run logistic_map --mu-min 3.5 --mu-max 4.0 --mu-steps 50 --n 200 --burn 100 --outdir outputs/logistic_map_demo
```

**Expected stdout (summary)**
```text
EXPERIMENT: logistic_map
OUTDIR: outputs/logistic_map_demo
WROTE: outputs/logistic_map_demo/summary.json
WROTE: outputs/logistic_map_demo/bifurcation.csv
WROTE: outputs/logistic_map_demo/bifurcation.png
STATUS: OK
```

**Artifacts (must exist)**
- `outputs/logistic_map_demo/summary.json`
- `outputs/logistic_map_demo/bifurcation.csv`
- `outputs/logistic_map_demo/bifurcation.png`

---

## 3) Damped oscillator (ODE integration)

Integrates a damped harmonic oscillator and saves a timeseries table and plot.

**Command**
```bash
python -m src.main run damped_oscillator --x0 1.0 --v0 0.0 --omega 2.0 --gamma 0.15 --t-max 20 --dt 0.01 --outdir outputs/oscillator_demo
```

**Expected stdout (summary)**
```text
EXPERIMENT: damped_oscillator
OUTDIR: outputs/oscillator_demo
WROTE: outputs/oscillator_demo/summary.json
WROTE: outputs/oscillator_demo/timeseries.csv
WROTE: outputs/oscillator_demo/timeseries.png
STATUS: OK
```

**Artifacts (must exist)**
- `outputs/oscillator_demo/summary.json`
- `outputs/oscillator_demo/timeseries.csv`
- `outputs/oscillator_demo/timeseries.png`

---

## 4) Symbolic series expansion (symbolic)

Computes and verifies a symbolic series expansion, then exports both a human-readable report and a machine-readable JSON record.

**Command**
```bash
python -m src.main run symbolic_series --expr "sin(x)/(1+x)" --about 0 --order 8 --outdir outputs/symbolic_demo
```

**Expected stdout (summary)**
```text
EXPERIMENT: symbolic_series
OUTDIR: outputs/symbolic_demo
WROTE: outputs/symbolic_demo/summary.json
WROTE: outputs/symbolic_demo/series.txt
WROTE: outputs/symbolic_demo/series.json
STATUS: OK
```

**Artifacts (must exist)**
- `outputs/symbolic_demo/summary.json`
- `outputs/symbolic_demo/series.txt`
- `outputs/symbolic_demo/series.json`

---

## 5) Re-running into an existing directory (idempotent overwrite)

If the output directory already exists, re-running should overwrite the same filenames (no random suffixes).

**Command**
```bash
python -m src.main run logistic_map --mu-min 3.7 --mu-max 3.9 --mu-steps 10 --n 100 --burn 50 --outdir outputs/logistic_map_demo
```

**Expected stdout (summary)**
```text
EXPERIMENT: logistic_map
OUTDIR: outputs/logistic_map_demo
WROTE: outputs/logistic_map_demo/summary.json
WROTE: outputs/logistic_map_demo/bifurcation.csv
WROTE: outputs/logistic_map_demo/bifurcation.png
STATUS: OK
```

**Artifacts (must exist; same names as before)**
- `outputs/logistic_map_demo/summary.json`
- `outputs/logistic_map_demo/bifurcation.csv`
- `outputs/logistic_map_demo/bifurcation.png`

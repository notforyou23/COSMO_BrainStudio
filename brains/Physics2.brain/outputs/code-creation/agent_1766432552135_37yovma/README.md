# generated_script_1766432556417 — Reproducible toy-model experiments

This repo is a small, reproducible “code interpreter friendly” sandbox for numerical/symbolic toy experiments that probe how classical-looking structure can emerge from quantum rules (and how diagnostics like entanglement respond under simple dynamics).

The emphasis is on **determinism** (seeded runs), **small-scale** models (lattices/graphs you can run on a laptop), and **artifact saving** (plots + tables you can re-generate byte-for-byte).
## What you can reproduce

Experiments are intentionally lightweight; each produces one or more plots and a CSV/JSON summary in an output directory:

- **Small lattice Hamiltonians (exact diagonalization)**: ground-state energy gaps and **bipartite entanglement entropy** vs. a control parameter.
- **Toy decoherence / “classicalization”**: a small system coupled to an environment; track purity/entropy and pointer-basis stability.
- **Symbolic mini-derivations**: closed-form checks (e.g., simple effective-action terms / beta-function-style flows) to validate numerics.

All experiments are runnable via `src/cli.py`, and share common utilities in `src/lib/io.py` (seeding + saving) and `src/lib/plotting.py` (styling + deterministic figure output).
## Installation

Requirements are pinned in `requirements.txt`.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows (PowerShell):
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```
## Quickstart (run one experiment)

All runs take a seed and an output directory. Re-running with the same args should reproduce the same files.

```bash
# Show available experiments / flags
python -m src.cli --help

# Example: exact diagonalization toy model with entanglement diagnostics
python -m src.cli run ising_ed --L 10 --g_min 0.2 --g_max 2.0 --num 25 --seed 0 --out outputs/ising_ed

# Example: system+environment toy decoherence diagnostic
python -m src.cli run decoherence --n_sys 1 --n_env 8 --steps 200 --seed 0 --out outputs/decoherence
```
## Outputs and reproducibility guarantees

Each run writes into `--out`:

- `metrics.json` (run configuration + scalar diagnostics)
- `summary.csv` (tabular results for parameter sweeps)
- `fig_*.png` (plots)

Reproducibility conventions used across experiments:

1. A single `--seed` controls `numpy` (and any other RNG used).
2. Plots are saved with fixed DPI and consistent style.
3. All parameters are serialized alongside results to make runs self-describing.

Tip: keep outputs from different runs separated (e.g., `outputs/<exp_name>/<timestamp_or_tag>`), especially when sweeping parameters.
## Common CLI patterns

```bash
# List experiments (if implemented by the CLI)
python -m src.cli list

# Run with a different seed and overwrite an existing directory (if supported)
python -m src.cli run ising_ed --seed 123 --out outputs/ising_ed_s123 --overwrite
```
## Interpreting the toy results (suggested checks)

- **Entanglement entropy**: peaks/rapid changes often correlate with crossovers/critical regions in small lattices.
- **Decoherence**: purity typically decays as the environment entangles with the system; “pointer states” are those least disturbed.
- **Symbolic vs numeric**: use symbolic outputs to sanity-check scalings/signs before trusting larger sweeps.

Because these are *toy* models, finite-size effects are expected; the goal is qualitative behavior and reproducible diagnostics, not precision estimates.
## Troubleshooting

- If plotting fails in headless environments, set a non-interactive backend:
  `export MPLBACKEND=Agg` (Linux/macOS) or `setx MPLBACKEND Agg` (Windows).
- If runs are slow, reduce lattice size (`--L`) / environment size (`--n_env`) or the number of sweep points (`--num`).
- If outputs differ between machines, confirm identical Python/package versions and that you are reusing the same `--seed`.
## License / intended use

This is a research prototype scaffold intended for experimentation and extension. The simplest way to add a new experiment is to implement a new subcommand in `src/cli.py` that:
1) parses parameters, 2) seeds via `src/lib/io.py`, 3) computes diagnostics, 4) saves CSV/JSON + plots deterministically.

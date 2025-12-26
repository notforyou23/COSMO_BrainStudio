# generated_script_1766435373331

Prototype numerical/symbolic toy experiments for exploring how *classical-looking structure* can emerge from simple quantum/statistical rules (entanglement diagnostics, coarse-graining flows, and minimal decoherence models). The repository is designed for **reproducible runs**: every experiment takes explicit parameters, a seed, and writes a self-contained result bundle (data + plots + metadata).
## Quickstart

### 1) Create an environment and install
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2) Discover experiments
```bash
python -m experiments list
```

### 3) Run an experiment (writes results to `runs/`)
```bash
python -m experiments run tfim_entanglement --L 10 --g 1.0 --seed 0
python -m experiments run decoherence_spin_bath --n_env 8 --coupling 0.4 --t_max 10 --seed 1
```

### 4) Re-run exactly (from saved metadata)
```bash
python -m experiments rerun runs/<run_id>/meta.json
```
## What you get (standardized outputs)

Each run creates a directory like:
```
runs/<run_id>/
  meta.json          # parameters, seed, versions, timestamps
  results.json       # primary scalars (e.g., entropies, gaps, fit params)
  table.csv          # tidy tabular output when applicable
  figures/
    *.png            # diagnostic plots
```

Common conventions:
- **Determinism**: supplying the same `--seed` reproduces stochastic components.
- **Portable artifacts**: JSON/CSV/PNG only (no notebook state required).
- **Small by default**: toy sizes that run in seconds; scale up via flags.
## Included toy-model experiments (Stage-1 set)

### 1) `tfim_entanglement` — exact diagonalization + entanglement
**Model:** 1D transverse-field Ising chain (small `L`, periodic or open boundary).  
**Goal:** show how ground-state entanglement varies across a quantum critical region.

**Diagnostics / outputs**
- Energy spectrum summary (ground energy, gap).
- Bipartite von Neumann entropy `S(ℓ)` for cuts `ℓ=1..L-1`.
- Optional scan over field strength `g` with a single plot:
  - `figures/entropy_vs_cut.png` (entropy profile at fixed `g`)
  - `figures/entropy_vs_g.png` (e.g., half-chain entropy vs `g`)

**Example command**
```bash
python -m experiments run tfim_entanglement --L 12 --g 0.5 --boundary open --seed 0
```
### 2) `decoherence_spin_bath` — minimal decoherence / pointer-basis emergence
**Model:** one system qubit coupled to an environment of `n_env` qubits (simple Ising-type interaction), with optional environment self-dynamics.  
**Goal:** demonstrate decay of off-diagonal density-matrix terms and the emergence of an approximate classical mixture in a preferred basis.

**Diagnostics / outputs**
- Reduced density matrix of the system vs time.
- Coherence measure (e.g., `|ρ01(t)|`) and purity `Tr(ρ^2)`.
- Entanglement proxy: system–environment mutual information (small sizes).

**Expected figures**
- `figures/coherence_vs_time.png`
- `figures/purity_vs_time.png`

**Example command**
```bash
python -m experiments run decoherence_spin_bath --n_env 10 --coupling 0.3 --t_max 8 --n_steps 200 --seed 42
```
### 3) `blockspin_rg_ising` — coarse-graining and effective couplings
**Model:** 2D Ising (tiny lattice) or 1D Ising with block-spin coarse-graining; estimate an effective coupling after decimation.  
**Goal:** illustrate the *direction* of RG flow and how macroscopic parameters can stabilize.

**Diagnostics / outputs**
- Estimated effective coupling(s) `K' = f(K)` for a grid of `K`.
- Flow plot comparing iterations of coarse-graining.

**Expected figures**
- `figures/rg_flow.png`
- `table.csv` with columns like `K, K_prime, iteration`.

**Example command**
```bash
python -m experiments run blockspin_rg_ising --L 16 --K_grid 0.1 1.0 20 --n_iter 4 --seed 0
```
## Reproducibility notes

- Runs record package versions and platform info in `meta.json`.
- Numerical linear algebra is kept to small sizes to avoid machine-dependent convergence issues.
- If you change BLAS/LAPACK backends, tiny floating-point differences are possible; the saved artifacts still document the configuration.

## Typical troubleshooting

- **`ModuleNotFoundError: experiments`**: ensure you installed with `pip install -e .` from the repo root.
- **Slow runs**: reduce system sizes (e.g., `--L`) or time steps (`--n_steps`); these are toy models by design.

## License
This project is intended as a research/education prototype; see repository metadata for licensing (if provided).

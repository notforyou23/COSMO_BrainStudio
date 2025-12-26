# Expected outputs (plots/tables) — toy experiments

This guide describes the **files you should see** after running each included experiment, plus a high-level interpretation of the diagnostics.

All runs are deterministic given the same CLI flags (notably `--seed`) and are written under an output directory of the form:

- `OUT/<experiment>/<experiment>_seed<seed>[_<name>]/...` (CLI experiments), or
- a user-specified `--out` / `--outdir` (standalone modules in `src/experiments/`).

---

## 1) `random-walk` (CLI)

Run (example):
```bash
python -m src.cli random-walk --out outputs_example --seed 0 --steps 200 --n 200
```

### Files produced
In `.../random_walk/random_walk_seed0/`:

- `args.json` — exact parameters used (`seed`, `steps`, `n`, etc.).
- `summary.json` — scalar summary statistics:
  - `final_mean`: mean of final position `x(T)` over trajectories
  - `final_var`: variance of `x(T)` over trajectories
- `trajectories.csv` — long-form table with columns:
  - `traj` (trajectory index), `t` (time step), `x` (position)
- `trajectories.png` — line plot of the first ~20 trajectories `x(t)`.
- `final_hist.png` — histogram estimate of the final-position distribution `x(T)`.

### How to interpret
- `final_hist.png` should look approximately symmetric and bell-shaped around 0.
- `final_var` should scale roughly like `T` (diffusive scaling), illustrating how a macroscopic “classical” distribution emerges from simple microscopic stochastic rules.

---

## 2) `two-qubit-entanglement` (CLI)

Run (example):
```bash
python -m src.cli two-qubit-entanglement --out outputs_example --seed 0 --n 5000
```

### Files produced
In `.../two_qubit_entanglement/two_qubit_entanglement_seed0/`:

- `args.json` — exact parameters used (`seed`, `n`).
- `summary.json` — includes:
  - `mean_S`: mean entanglement entropy (bits) over sampled states
- `entropies.csv` — per-sample entanglement entropy table:
  - `i` (sample index), `S_bits` (von Neumann entropy of subsystem A)
- `entropy_hist.png` — histogram of `S_bits` across Haar-random pure states.

### How to interpret
- `S_bits` is in `[0, 1]` for two qubits (maximal entanglement is 1 bit).
- The histogram should be biased toward larger entanglement (typical random pure states are highly entangled), serving as a baseline for “generic” quantum correlations.

---

# Standalone experiment modules (`src/experiments/`)

These are runnable directly as modules/scripts and are useful for numerical/symbolic diagnostics beyond the CLI surface.

## A) `rg_flow_toy` — 1D Ising decimation RG map

Run (example):
```bash
python -m src.experiments.rg_flow_toy --out outputs_example/rg_toy
```

### Files produced (`--out` directory)
- `rg_table.csv` — grid table with columns:
  - `K` (coupling), `K_prime` (after decimation), `beta` = `K_prime - K`
- `rg_beta.png` — plot of the discrete beta function `beta(K)`.
- `rg_map.png` — plot of `K'` vs `K` with the diagonal `K'=K` (fixed points at intersections).
- `flow_trajectories.png` — several iterated RG flows `K_n` vs step `n`.
- `meta.json` — configuration + notes + estimated small-`K` asymptotics.

### How to interpret
- For this exact 1D map, `K=0` is a stable fixed point (flows toward the disordered limit under decimation).
- `rg_map.png` and `flow_trajectories.png` visualize how coarse-graining changes effective couplings; `rg_beta.png` summarizes this as a “flow field”.

## B) `entanglement_diagnostics` — exact/state-prep entanglement checks

Run (example, prints dict rows to stdout):
```bash
python -m src.experiments.entanglement_diagnostics
```

### Output produced (stdout)
A small list of JSON-like dictionaries (one per case) with keys such as:
- `name`, `n` (qubit count)
- `partition_A`, `partition_B` (subsystems)
- `S_A`, `S_B` (entanglement entropies in bits)
- `I_AB` (mutual information in bits)

### How to interpret
- **Bell**: `S_A ≈ 1`, `I_AB ≈ 2` (maximally entangled pair).
- **GHZ**: single-qubit vs rest has `S ≈ 1`, while pairwise correlations reflect global entanglement structure.
- **TFIM ground state**: varying `h` changes how entanglement spreads across the bipartition, giving a toy signature of “more/less correlated” phases.

## C) `emergent_classicality_graph` — unitary entangling + dephasing (“pointer basis”)

Run (example):
```bash
python -m src.experiments.emergent_classicality_graph --outdir outputs_example/emergent_graph --seed 0
```

### Files produced (`--outdir` directory)
- `coherence_pointer_basis.png` — coherence (normalized off-diagonal L1 mass) vs step in:
  - the dephasing/pointer **Z** basis
  - the complementary **X** basis
- `entropy_growth.png` — von Neumann entropy vs step (mixing due to dephasing).

### How to interpret
- Coherence in the **Z basis** should decay fastest (environment monitors Z), while coherence in **X** can persist differently.
- Entropy typically increases from 0 as the state becomes mixed, illustrating a minimal “classicalization” mechanism: information leakage selects a preferred basis and suppresses superpositions in that basis.

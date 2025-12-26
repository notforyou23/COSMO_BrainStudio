# generated_script_1766430415667

Prototype numerical/symbolic experiments illustrating how *classical-looking structure* can emerge from simple quantum-inspired rules, and how *entanglement structure* can be mapped to an “emergent geometry” on graphs.

The project is intentionally small and reproducible: all experiments are seeded, write their artifacts to `outputs/`, and print compact tables in the terminal.

## Quickstart

```bash
# from the project root
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

pip install -e .
# list experiments & options
python -m generated_script_1766430415667.cli --help
```

Run all experiments (recommended first run):

```bash
python -m generated_script_1766430415667.cli run-all --seed 0 --outdir outputs
```

Run one experiment:

```bash
python -m generated_script_1766430415667.cli ising --L 16 --steps 4000 --schedule linear --seed 1 --outdir outputs
python -m generated_script_1766430415667.cli entanglement-graph --n 10 --samples 200 --state haar --seed 2 --outdir outputs
python -m generated_script_1766430415667.cli symbolic-flow --model phi4 --d 2 --seed 3 --outdir outputs
```

Artifacts are written under `outputs/` with timestamped subfolders (CSV + PNG; some runs also emit a small JSON manifest).
## Experiments

### 1) Toy Ising “emergent classicality” proxy
**Module:** `src/experiments/toy_ising_emergent_classicality.py`  
**Idea:** use a small 2D Ising-like lattice as a *proxy* for a system transitioning from disordered/“quantum-noisy” to ordered/“classical” under an annealing/noise schedule.  
**Diagnostics:**
- magnetization `m` and susceptibility-like variance
- two-point correlation length estimate (from spatial correlations)
- entropy proxy (e.g., histogram entropy of local spin blocks / domain distribution)

**Typical outputs (saved in `outputs/.../`):**
- `ising_summary.csv` (per temperature/noise step): columns like `T, m_mean, m_var, corr_len, entropy_proxy`
- `ising_magnetization.png`: `m` vs `T` (or schedule step)
- `ising_entropy_corrlen.png`: entropy proxy and correlation length vs `T`

**What to look for:** as the schedule cools/denoises, entropy proxy decreases while correlation length and |m| increase—capturing “classicalization” as stable macroscopic order.

Example terminal table (shape only):
```
step    T     m_mean  corr_len  entropy
0     3.00    0.02     0.8       2.7
...
N     0.50    0.92     4.1       0.6
```
### 2) Entanglement graph → emergent geometry diagnostic
**Module:** `src/experiments/entanglement_graph_geometry.py`  
**Idea:** sample toy many-body states (Haar-random small systems and/or stabilizer-like constructions), compute bipartite entanglement entropies, then interpret mutual-information-like weights as edges of a graph. Compare shortest-path distances in this graph to entanglement structure.

**Diagnostics:**
- single-site and bipartition entanglement entropies (von Neumann or Rényi-2 proxy)
- mutual information matrix `I(i:j)` → weighted graph
- emergent distances `d(i,j)` from shortest paths on the graph
- correlations: `corr( I(i:j), 1/d(i,j) )`, embeddings (optional)

**Typical outputs:**
- `entanglement_mi_matrix.csv`: symmetric matrix of `I(i:j)`
- `entanglement_distance_matrix.csv`: graph shortest-path distances
- `entanglement_scatter.png`: scatter of `I(i:j)` vs `d(i,j)` (or `1/d`)
- `entanglement_summary.csv`: correlations and basic stats per sample batch

**What to look for:** structured (non-Haar) states yield more geometric signal: high mutual information tends to correspond to short graph distances; Haar states tend to be close to featureless.

Example summary row:
```
state=stabilizer_like, n=10, samples=200, corr_I_invD=0.71, mean_S1=0.52
```
### 3) Symbolic “flow” / effective model toy derivation (RG-like)
**Module:** `src/experiments/symbolic_flow.py` (entry point via CLI `symbolic-flow`)  
**Idea:** perform a small symbolic manipulation that mimics an effective-action / renormalization step for a simple model (e.g., φ⁴ in low dimension or a 1D coarse-graining). This is *not* a full field-theory engine—just a transparent derivation you can inspect.

**Diagnostics / artifacts:**
- derived beta-function-like update rules (symbolic)
- numeric evaluation of the flow for chosen initial couplings
- stability classification (fixed points / linearized eigenvalues)

**Typical outputs:**
- `flow_equations.txt` (pretty-printed sympy expressions)
- `flow_trajectory.csv`: columns like `k, g(k), m2(k), lambda(k)`
- `flow_phaseplot.png`: simple 2D projection of trajectories

**What to look for:** flows that approach a stable fixed point correspond to scale-invariant “effective classical” behavior; runaway flows indicate instability/ordering transitions depending on the toy model.
## Reproducibility notes
- All commands accept `--seed` and write a small `run_manifest.json` recording parameters, package versions (when available), and output file names.
- All numeric results are small-scale by design and intended for *illustration*, not precision physics.

## Directory layout (expected)
```
src/
  cli.py
  experiments/
    toy_ising_emergent_classicality.py
    entanglement_graph_geometry.py
    symbolic_flow.py
outputs/
  YYYYMMDD_HHMMSS_.../
    *.csv
    *.png
    run_manifest.json
```

## License
Prototype research code; treat as MIT-like unless your deployment requires a stricter policy.

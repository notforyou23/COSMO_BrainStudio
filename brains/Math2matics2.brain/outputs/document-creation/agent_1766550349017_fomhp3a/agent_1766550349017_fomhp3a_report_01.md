## /outputs/roadmap_v1.md — insert subsection

### Computational Content Requirements (mandatory per subtopic)
Every subtopic (i.e., each “cell” in the roadmap / coverage plan) must include **all** computational elements below. These requirements come directly from the Sub-goal 3/7 directive to “specify computational content per cell” with (i) SymPy symbolic derivations, (ii) numerical algorithms with solver and convergence criteria, (iii) parameter sweep definitions, and (iv) unit tests + acceptance thresholds.

#### 1) SymPy derivation (mandatory)
Each subtopic must include a **reproducible symbolic derivation in SymPy** that produces the exact objects later used numerically.
Required artifacts per subtopic:
- **Symbol definitions** (SymPy symbols) and any stated assumptions needed for correctness.
- **Derivation steps** (not just final expressions) sufficient to regenerate:
  - governing equations / transforms used in the subtopic,
  - closed-form expressions or reduced forms that feed the numerical method,
  - any Jacobians/gradients or related linearizations when the subtopic uses local linear structure (consistent with the project’s emphasis on derivatives as local linear predictors).
- **Export/hand-off**: explicit statement of what symbolic output is passed to the numerical stage (e.g., lambdified function, simplified expression).

#### 2) Numerical method (mandatory)
Each subtopic must specify at least one **numerical algorithm** and how it is executed.
Required artifacts per subtopic:
- **Algorithm choice** (e.g., “solve X via SciPy solver Y” or an explicitly described iterative scheme).
- **Convergence / stopping criteria** (explicit tolerances and/or max-iteration rules).
- **Stability considerations** when multiplicative updates or extreme scales are involved:
  - If the subtopic involves sequential multiplicative updating, it must use **log-odds** rather than raw odds for numerical stability (per the consistency review note that odds updates can underflow/overflow and log-odds turns multiplicative updates into additive ones).
- **Tooling constraint alignment**: implementation must be compatible with the common toolchain stated in the Computational Plan: **Python 3.11+, SymPy, NumPy, SciPy, Matplotlib/Seaborn, pytest**.

#### 3) Parameter sweep specification (mandatory)
Each subtopic must define a **parameter sweep** that probes behavior beyond a single hand-picked configuration.
Required artifacts per subtopic:
- **Parameter list**: which parameters are swept and which are held fixed.
- **Ranges**: explicit numeric min/max (or discrete set).
- **Resolution**: number of points per dimension.
- **Sampling strategy**: how points are selected (e.g., uniform grid vs other declared strategy).
- **Output metrics** captured across the sweep (what is plotted/tabulated and what summary statistics are recorded).

#### 4) Verification checks (unit tests + acceptance thresholds) (mandatory)
Each subtopic must include automated verification and explicit pass/fail thresholds.
Required artifacts per subtopic:
- **pytest unit tests** for:
  - symbolic-to-numeric consistency (e.g., lambdified functions agree with expected forms at representative points),
  - numerical solver sanity (convergence achieved under declared stopping rules),
  - invariants or known-equality cases when available.
- **Acceptance thresholds** must be numeric and stated:
  - error tolerances for equality/approximation checks,
  - bounds on residuals or constraint violations,
  - thresholds for sweep-level results (e.g., monotonicity or stability classification consistency when relevant).
- **Inference caveat check** when OLS-style linear regression is used on empirical data:
  - If errors are **heteroscedastic or heavy-tailed**, the subtopic must explicitly note that standard OLS inference can be misleading—specifically, such violations can produce biased/invalid uncertainty quantification (confidence intervals and p-values) and must be checked/mitigated (consistent with the project’s recorded caution that local linearity assumptions can mask heteroscedasticity/outliers and yield misleading inference).

---

## /outputs/coverage_matrix.csv — reflect requirements as columns

Add the following **mandatory columns** to the coverage matrix so every subtopic row can be audited for computational completeness:

New columns (exact intent):
1. `sympy_derivation_required`  
   - Expected values: `Y/N` (must be `Y` for all subtopics under this mandate)
2. `numerical_method_specified`  
   - Expected values: `Y/N` (must be `Y`)
3. `solver_and_convergence_criteria`  
   - Expected values: `Y/N` (must be `Y`)
4. `parameter_sweep_defined`  
   - Expected values: `Y/N` (must be `Y`)
5. `sweep_range`  
   - Free text / structured text (must be non-empty): explicit min/max or discrete set
6. `sweep_resolution`  
   - Free text / integer (must be non-empty): number of points / step size
7. `sweep_sampling_strategy`  
   - Free text (must be non-empty): grid/uniform/etc. as declared
8. `verification_checks_pytest`  
   - Expected values: `Y/N` (must be `Y`)
9. `acceptance_thresholds_numeric`  
   - Expected values: `Y/N` (must be `Y`)
10. `stability_notes_log_odds_if_applicable`  
   - Expected values: `Y/N/NA` (must be `Y` if the subtopic uses multiplicative odds-style updates; otherwise `NA`)
11. `ols_inference_caveat_if_applicable`  
   - Expected values: `Y/N/NA` (must be `Y` if the subtopic uses OLS on potentially heteroscedastic/heavy-tailed/noisy data; otherwise `NA`)

### How to use these columns
- A coverage row is **computationally complete** only if the required fields are populated and the `Y/NA` logic is satisfied.
- This directly operationalizes the Sub-goal 3/7 requirement: “required SymPy symbolic derivations, numerical algorithms (solver choices, convergence criteria), parameter sweep definitions (ranges, resolution, sampling strategy), unit tests, and acceptance thresholds.”

---

## Conclusion
The roadmap now has an explicit, mandatory **Computational Content Requirements** subsection that forces each subtopic to include: **(1) a SymPy derivation, (2) a specified numerical method with solver and convergence criteria, (3) a parameter sweep with range/resolution/sampling, and (4) verification via pytest plus numeric acceptance thresholds**, with two conditional checks grounded in existing project findings (log-odds for numerical stability in multiplicative updates; explicit caution when applying OLS under heteroscedastic/heavy-tailed conditions). The coverage matrix is extended with concrete columns so these requirements are auditable per subtopic row rather than implicit.
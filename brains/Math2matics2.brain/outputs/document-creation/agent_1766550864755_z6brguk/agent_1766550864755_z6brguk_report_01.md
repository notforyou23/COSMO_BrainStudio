## Toy experiment output contract + determinism test (what to add)

This mission is explicitly scoped in the stored project prompts: define a **fixed output contract** (artifacts + schema), **seed all RNGs**, implement a **small deterministic toy experiment** (example given: *heavy‑tailed mean vs median‑of‑means*), and add a **pytest** that verifies stability across runs with the same seed (stable hashes *or* invariant fields). The guidance appears repeatedly in the captured prompts (all dated **2025‑12‑24**), including the requirement to write `./outputs/results.json` and `./outputs/figure.png` and to enforce determinism in code and tests.

### 1) Output contract (required artifacts and required fields)

#### Required artifact paths
- `./outputs/results.json`
- `./outputs/figure.png`

These two paths are the “fixed artifact schema” repeatedly specified in the prompts (e.g., “Define a fixed artifact schema (e.g., outputs/results.json + outputs/figure.png)” and “Define a fixed output contract (e.g., ./outputs/results.json with required keys + ./outputs/figure.png)”).

#### `./outputs/results.json` schema (minimum required keys)
The mission statement requires **seed, parameters, metrics**. The stored prompts also repeatedly require a **schema/version field** (“stable results schema (fields + version) for /outputs/results.json”).

Use this minimal, explicit contract:

```json
{
  "contract_version": "1.0",
  "seed": 123,
  "parameters": { ... },
  "metrics": { ... }
}
```

Notes grounded in memory:
- A constant `DEFAULT_CONTRACT_VERSION = "1.0"` appears in the captured `run_toy_experiment.py` snippet (INTROSPECTION item 6), so the contract version being `"1.0"` is consistent with the code the project started to build.
- The mission summary explicitly asks for “(with seed, parameters, metrics)”.

#### `./outputs/figure.png` contract (fixed size/style)
The prompts explicitly demand “fixed size/style” and “consistent naming” so the figure output is deterministic. Concretely, the contract should include:
- The filename fixed as `figure.png`
- A fixed canvas size (width/height)
- A fixed style configuration (the same plotting parameters each run)

(Those are the only style constraints stated in memory; no additional plotting backend choices are stated in the knowledge provided.)

---

### 2) Deterministic toy experiment (what it must do)

The stored prompts give a concrete example toy experiment: **“heavy‑tailed mean vs median‑of‑means”**. The implementation should therefore:
1. Take a single `seed` input (CLI arg or default).
2. Seed all RNG sources used:
   - Python’s `random`
   - NumPy RNG (`numpy.random`)
3. Generate a heavy‑tailed sample in a deterministic way given the seed.
4. Compute metrics that compare:
   - The plain sample mean
   - A median‑of‑means estimator
5. Write the results to `./outputs/results.json` using the fixed schema above.
6. Generate and save a plot to `./outputs/figure.png` using fixed size/style.

This is exactly aligned with the repeated mission wording: “seed the RNG(s), and add a small deterministic toy experiment (e.g., heavy-tailed mean vs median-of-means) that always writes the same schema.”

---

### 3) `pytest` requirement: stable across runs with the same seed

The stored prompts describe two acceptable verification approaches:
- “add a pytest verifying stable hashes”
- or verify “invariant fields across runs with the same seed”
- and in another prompt: “add a test asserting exact keys/fields exist and values are within expected tolerances.”

To satisfy the mission as stated (stable across runs **with the same seed**), the test should do **two runs** of the experiment using the same seed and then assert:

#### (A) Schema invariants (must always hold)
- `contract_version` exists and equals `"1.0"` (consistent with `DEFAULT_CONTRACT_VERSION = "1.0"` in the captured snippet)
- `seed` exists and equals the provided seed
- `parameters` exists (object)
- `metrics` exists (object)

#### (B) Determinism check (choose one of these, both mentioned in memory)
1) **Stable hash check (strict):**
- Compute a hash (e.g., SHA256) of `outputs/results.json` and assert it is identical across the two runs.
- Optionally also hash `outputs/figure.png` and assert identical across runs (the prompts explicitly call for deterministic plotting parameters and figure determinism, and also mention “ensure identical bytes/values across runs given the same seed.”)

2) **Invariant fields check (less strict but allowed by the mission wording):**
- Parse both JSON files and assert that key numeric outputs in `metrics` match exactly (or within a tolerance, as one prompt suggests), and that the required keys match exactly.
- This approach is explicitly supported by the prompt that says tests may check “values are within expected tolerances.”

The mission statement asks for “stable hashes **or** invariant fields,” so either one satisfies the stated requirement, but the stored prompts also include an explicit “ensure identical bytes/values across runs given the same seed” requirement, which supports hashing as the stronger and simpler criterion if determinism is fully controlled.

---

### 4) Where to put this in the project (grounded to the stored file evidence)

A partial `run_toy_experiment.py` is present in memory (INTROSPECTION item 6) showing:
- `DEFAULT_CONTRACT_VERSION = "1.0"`
- A `WORKDIR` set to an absolute path: `Path("/Users/jtr/_JTR23_/COSMO/runtime/outputs/execution")`
- `OUTPUTS_DIR = WORKDIR / "outputs"`
- and then it truncates at `RESULTS_PATH = OUT...`

The mission, however, requires writing to **relative paths**:
- `./outputs/results.json`
- `./outputs/figure.png`

So the concrete change required is: the implementation must not hardcode an absolute `WORKDIR` if the contract is explicitly `./outputs/...`. The prompts consistently refer to `./outputs/…` as the stable contract.

---

## Implementation checklist (what must be true after changes)

1. Running the toy experiment produces exactly:
   - `outputs/results.json`
   - `outputs/figure.png`

2. `results.json` includes, at minimum:
   - `contract_version: "1.0"` (consistent with the captured constant)
   - `seed`
   - `parameters`
   - `metrics`

3. RNG determinism:
   - Both Python `random` and NumPy are seeded from the same `seed`.

4. Plot determinism:
   - Fixed size and style are explicitly set (the prompts require this; no extra plotting assumptions are introduced beyond “fixed size/style”).

5. Test determinism:
   - A `pytest` runs the experiment twice with the same seed.
   - It asserts either:
     - stable hashes of `results.json` (and optionally `figure.png`), **or**
     - invariant fields across runs (schema keys + metric values), consistent with the prompt guidance.

---

## Conclusion

The stored project instructions (all dated **2025‑12‑24**) converge on a single deliverable: a deterministic toy experiment (explicitly suggested: **heavy‑tailed mean vs median‑of‑means**) that **always** writes a fixed output contract consisting of `./outputs/results.json` (including **contract version, seed, parameters, metrics**) and a deterministic `./outputs/figure.png` (fixed size/style). A `pytest` must run the experiment twice with the same seed and verify determinism either by **stable hashes** or by asserting **invariant schema fields and metrics**. The partial `run_toy_experiment.py` evidence already contains `DEFAULT_CONTRACT_VERSION = "1.0"`, which should be used as the contract version to make the JSON schema explicit and stable.
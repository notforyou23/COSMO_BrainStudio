# ICE vs Conversion vs BEV — Runner + CSV Template

This project provides a runnable Jupyter notebook and a user-editable CSV template to compare:
- **ICE (baseline)** vs **EV conversion** vs **BEV** outcomes
- Total cost of ownership (TCO) components and energy/fuel use
- Results across **segments** (fleet, classic, specialty) and **drive-cycle proxies** (urban/last-mile, mixed, highway)
- Quick **sensitivity toggles** (energy price, utilization, battery replacement, financing)
## Directory layout (expected)

- `notebooks/ice_vs_conversion_vs_bev.ipynb` — main runnable notebook
- `outputs/template_user_inputs.csv` — user inputs + scenario toggles (edit this)
- `src/evconv_config/assumptions.py` — default assumptions by segment + merge/validation logic
- `src/evconv_config/drive_cycles.py` — built-in drive-cycle proxies + selection/resampling helpers
## How to run

1. Start Jupyter from this project root:
   - `jupyter lab` (or `jupyter notebook`)
2. Open: `notebooks/ice_vs_conversion_vs_bev.ipynb`
3. Run all cells from top to bottom.
4. Edit inputs in `outputs/template_user_inputs.csv`, then re-run the notebook to refresh results.

Notes:
- The notebook is designed so **the CSV is the only file most users edit**.
- The notebook applies **segment defaults** first, then **merges your CSV overrides**, then applies **sensitivity toggles**.
## Editing the CSV template

Open `outputs/template_user_inputs.csv` and adjust:
- Vehicle identifiers (name/ID) and scenario selection (ICE / conversion / BEV)
- Segment: `fleet`, `classic`, or `specialty`
- Drive-cycle proxy: `urban_last_mile`, `mixed`, or `highway`
- Key operational parameters (annual miles, days/year, payload if present)
- Energy/fuel prices and efficiency parameters (or leave blank to use defaults)
- Financial parameters (discount rate, term, down payment, etc.)
- Sensitivity toggles (see below)

General rules:
- **Blank cells mean “use defaults.”** A filled value overrides the segment default.
- Keep units consistent with the column headers (the notebook prints units used at load time).
- If you switch a segment or cycle, re-run the notebook so assumptions and cycles are re-applied.
## Segments and default assumptions

The notebook selects a **segment** per row and loads a corresponding default assumption set:
- **fleet**: high utilization, cost-sensitive, structured downtime/maintenance assumptions
- **classic**: lower utilization, preservation/limited-mileage patterns, different ownership horizon
- **specialty**: duty- or role-specific usage, potentially higher auxiliary loads and service needs

What defaults typically cover:
- Annual utilization patterns (miles/year, operating days)
- Energy/fuel baseline prices (can be overridden)
- Maintenance, tires, and other OPEX factors (as modeled in the notebook)
- Battery replacement policy defaults (if conversion/BEV)
- Financing/ownership defaults (term, APR, discount rate) when enabled

Override behavior:
- The system applies defaults first, then merges your per-row CSV values.
- If a value conflicts or is invalid, the notebook will raise a validation error identifying the field/row.
## Drive-cycle proxies (preloaded)

Choose one of the built-in proxies to approximate speed-vs-time behavior:
- `urban_last_mile`: stop-and-go, lower speeds, more transients (delivery/urban)
- `mixed`: blended urban/suburban behavior
- `highway`: steadier speeds, fewer stops, higher average speed

How cycles are used:
- Cycles are stored as time-speed profiles and are **resampled as needed** for consistent computation.
- The notebook uses the selected cycle to estimate relative energy use impacts across scenarios (ICE vs conversion vs BEV).
- If you change cycle selection in the CSV, re-run to update computed energy/consumption and derived costs.
## Sensitivity toggles (scenario switches)

The template includes “toggle” fields intended to support fast what-if analysis. Typical toggles include:

1) Energy price sensitivity
- Purpose: test electricity and/or fuel price changes.
- How it works: applies multipliers or override prices to the baseline energy inputs.
- Use when: evaluating exposure to charging tariffs, diesel volatility, demand charges proxies (if modeled).

2) Utilization sensitivity
- Purpose: test higher/lower annual miles or operating intensity.
- How it works: scales annual miles (and related wear/energy) while keeping the vehicle constant.
- Use when: comparing routes, shift patterns, seasonal volume changes.

3) Battery replacement sensitivity
- Purpose: include/exclude a mid-life pack replacement (conversion/BEV).
- How it works: enables a replacement event at a configured year/mileage with a configured cost.
- Use when: evaluating lifecycle risk, warranty assumptions, second-life packs, or conservative planning.

4) Financing sensitivity
- Purpose: switch between cash purchase vs financed purchase (or adjust APR/term).
- How it works: changes cashflow timing and cost of capital assumptions used in TCO.
- Use when: comparing procurement strategies and rate sensitivity.

Important:
- Toggles are applied **after** defaults and CSV overrides so you can keep a stable base case.
- If a toggle is enabled, the notebook will surface the effective values used in the scenario summary tables.
## Outputs and how to interpret them

The notebook produces:
- Scenario tables comparing **ICE vs conversion vs BEV** for:
  - Energy/fuel consumption and cost
  - CAPEX (vehicle, conversion kit, battery, charging equipment if modeled)
  - OPEX (energy, maintenance, tires, etc. as modeled)
  - Finance/discounting impacts (if enabled)
  - Total cost (e.g., NPV or undiscounted totals, depending on settings)
- Plots to compare:
  - TCO breakdown bars by scenario
  - Sensitivity deltas (base vs toggled cases)
  - Per-mile or per-year cost curves (if included)

Reading results:
- Compare **per-mile** metrics when utilization differs; compare **total** when the mission is fixed.
- If BEV/conversion looks worse on total cost, check whether:
  - utilization is too low to amortize CAPEX,
  - energy prices assumptions are unfavorable,
  - battery replacement is enabled/too early,
  - financing assumptions differ across scenarios.

Reproducibility tip:
- Keep a copy of your edited CSV per run (e.g., rename with a date) so results can be traced back to inputs.
## Troubleshooting

- Notebook fails on load/validation:
  - Confirm the CSV has the expected headers and segment/cycle values are spelled correctly.
  - Ensure numeric fields contain numbers (no stray commas or currency symbols).
- Results don’t change after editing CSV:
  - Re-run the cell that loads the CSV, or “Run All”.
  - Confirm you edited `outputs/template_user_inputs.csv` (not a copy elsewhere).
- Cycle/segment changes seem ignored:
  - Ensure the row’s segment/cycle fields are filled and match allowed values.
  - Check the scenario summary table for the “effective” assumptions used.

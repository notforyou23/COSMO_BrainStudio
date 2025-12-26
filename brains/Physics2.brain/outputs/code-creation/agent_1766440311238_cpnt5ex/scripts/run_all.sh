#!/usr/bin/env bash
set -euo pipefail

# Run all prototype experiments and generate a complete set of artifacts.
# Usage:
#   ./scripts/run_all.sh
# Optional env:
#   PYTHON=python3        # interpreter to use
#   OUTBASE=outputs       # base output directory (default: outputs)
#   NO_PLOT=1             # pass --no-plot to experiments
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PY="${PYTHON:-python}"
if ! "${PY}" -c "import sys; print(sys.version_info[:2])" >/dev/null 2>&1; then
  PY=python3
fi

OUTBASE="${OUTBASE:-outputs}"
NO_PLOT_FLAG=""
if [[ "${NO_PLOT:-0}" != "0" ]]; then
  NO_PLOT_FLAG="--no-plot"
fi

mkdir -p "${OUTBASE}"
echo "==> Listing available experiments"
"${PY}" -m src.main list

echo "==> Running: logistic_map"
"${PY}" -m src.main run logistic_map   --mu-min 3.5 --mu-max 4.0 --mu-steps 50   --n 200 --burn 100   ${NO_PLOT_FLAG}   --outdir "${OUTBASE}/logistic_map_demo"

echo "==> Running: damped_oscillator"
"${PY}" -m src.main run damped_oscillator   --x0 1.0 --v0 0.0 --omega 2.0 --gamma 0.15   --t-max 20 --dt 0.01   ${NO_PLOT_FLAG}   --outdir "${OUTBASE}/oscillator_demo"

echo "==> Running: symbolic_series"
"${PY}" -m src.main run symbolic_series   --expr "sin(x)/(1+x)" --about 0 --order 8   --outdir "${OUTBASE}/symbolic_demo"

echo "ALL_DONE: artifacts written under ${OUTBASE}/"

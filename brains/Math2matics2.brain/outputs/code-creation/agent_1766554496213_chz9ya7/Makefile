SHELL := /bin/bash
.DEFAULT_GOAL := help

OUTPUTS_DIR ?= outputs
HASHES_FILE ?= $(OUTPUTS_DIR)/hashes.json
NODE ?= node
NPM ?= npm

# Override PIPELINE_CMD for your project, e.g.:
#   make pipeline PIPELINE_CMD="npm run pipeline"
#   make repro PIPELINE_CMD="node scripts/run_pipeline.js"
PIPELINE_CMD ?= $(NPM) run pipeline

.PHONY: help pipeline hash-outputs update-hashes repro ci clean-outputs

help:
	@echo "Targets:"
	@echo "  pipeline        Run the pipeline once (writes into ./outputs/)."
	@echo "  hash-outputs    Compute stable SHA256 mapping for ./outputs/ -> outputs/hashes.json."
	@echo "  update-hashes   Alias for hash-outputs (updates expected hashes in-repo)."
	@echo "  repro           Run reproducibility check (run twice + compare; also validates hashes.json if present)."
	@echo "  ci              CI-aligned local target: clean outputs then run repro."
	@echo ""
	@echo "Vars:"
	@echo "  PIPELINE_CMD    Command used by scripts to run the pipeline (default: 'npm run pipeline')."
	@echo "  OUTPUTS_DIR     Output directory (default: outputs)."
	@echo "  HASHES_FILE     Expected hash file (default: outputs/hashes.json)."

$(OUTPUTS_DIR):
	@mkdir -p "$(OUTPUTS_DIR)"

pipeline: $(OUTPUTS_DIR)
	@echo "[pipeline] Running: $(PIPELINE_CMD)"
	@$(PIPELINE_CMD)

hash-outputs: $(OUTPUTS_DIR)
	@echo "[hash-outputs] Writing $(HASHES_FILE)"
	@PIPELINE_CMD='$(PIPELINE_CMD)' OUTPUTS_DIR='$(OUTPUTS_DIR)' HASHES_FILE='$(HASHES_FILE)' \
		$(NODE) scripts/hash_outputs.js

update-hashes: hash-outputs

repro: $(OUTPUTS_DIR)
	@echo "[repro] Running reproducibility check"
	@PIPELINE_CMD='$(PIPELINE_CMD)' OUTPUTS_DIR='$(OUTPUTS_DIR)' HASHES_FILE='$(HASHES_FILE)' \
		$(NODE) scripts/reproducibility_check.js

clean-outputs:
	@echo "[clean] Removing $(OUTPUTS_DIR)/"
	@rm -rf "$(OUTPUTS_DIR)"

ci: clean-outputs repro

SHELL := /bin/bash

# ---- Config (override as needed) ----
OUTPUTS_DIR ?= outputs
HASHES_FILE ?= $(OUTPUTS_DIR)/hashes.json
NODE ?= node

# Command to run your pipeline once (override in CI/local: make PIPELINE_CMD="...")
PIPELINE_CMD ?= npm run -s pipeline

# Scripts (expected to exist in-repo)
HASH_SCRIPT ?= scripts/hash_outputs.js
REPRO_SCRIPT ?= scripts/reproducibility_check.js

# ---- Targets ----
.PHONY: help all run pipeline clean-outputs hashes update-hashes repro ci

help:
	@echo "Targets:"
	@echo "  run / pipeline       Run pipeline once (PIPELINE_CMD=$(PIPELINE_CMD))"
	@echo "  hashes               Write $(HASHES_FILE) from current $(OUTPUTS_DIR)/ (deterministic)"
	@echo "  update-hashes        Alias: hashes"
	@echo "  repro                Run pipeline twice + compare artifact hashes; also validate against $(HASHES_FILE) if present"
	@echo "  ci                   CI-aligned: repro"
	@echo ""
	@echo "Variables:"
	@echo "  PIPELINE_CMD, OUTPUTS_DIR, HASHES_FILE, NODE, HASH_SCRIPT, REPRO_SCRIPT"

all: repro

run: pipeline
pipeline:
	@set -euo pipefail; \
	echo ">> Running pipeline: $(PIPELINE_CMD)"; \
	$(PIPELINE_CMD)

clean-outputs:
	@set -euo pipefail; \
	rm -rf "$(OUTPUTS_DIR)"; \
	mkdir -p "$(OUTPUTS_DIR)"; \
	echo ">> Cleaned $(OUTPUTS_DIR)/"

hashes:
	@set -euo pipefail; \
	mkdir -p "$(OUTPUTS_DIR)"; \
	if [ ! -f "$(HASH_SCRIPT)" ]; then \
		echo "ERROR: missing $(HASH_SCRIPT)"; exit 2; \
	fi; \
	echo ">> Writing $(HASHES_FILE)"; \
	"$(NODE)" "$(HASH_SCRIPT)" --outputs "$(OUTPUTS_DIR)" --out "$(HASHES_FILE)"

update-hashes: hashes

repro:
	@set -euo pipefail; \
	if [ ! -f "$(REPRO_SCRIPT)" ]; then \
		echo "ERROR: missing $(REPRO_SCRIPT)"; exit 2; \
	fi; \
	echo ">> Reproducibility check (runs pipeline twice, compares hashes; validates against $(HASHES_FILE) if present)"; \
	"$(NODE)" "$(REPRO_SCRIPT)" --pipeline "$(PIPELINE_CMD)" --outputs "$(OUTPUTS_DIR)" --hashes "$(HASHES_FILE)"

ci: repro

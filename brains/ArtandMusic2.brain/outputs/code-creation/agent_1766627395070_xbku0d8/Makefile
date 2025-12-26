SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

PYTHON ?= python3

QA_OUT_DIR := outputs/qa

.PHONY: help qa qa-run qa-clean scaffold

help:
	@echo "Targets:"
	@echo "  make qa        Run scaffold generation + assertions via tools/qa_run.py (fails fast)"
	@echo "  make scaffold  Alias for qa (single pipeline entrypoint)"
	@echo "  make qa-clean  Remove QA outputs"

# Single QA pipeline entrypoint: scaffolding + deterministic validations
qa: $(QA_OUT_DIR)
	$(PYTHON) tools/qa_run.py

# Alias kept for readability in docs/CI
scaffold: qa

qa-run: qa

$(QA_OUT_DIR):
	mkdir -p "$(QA_OUT_DIR)"

qa-clean:
	rm -rf "$(QA_OUT_DIR)"

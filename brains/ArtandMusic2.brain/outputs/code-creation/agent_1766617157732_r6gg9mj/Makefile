SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c

PYTHON ?= python3
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
SCRIPTS := $(ROOT)/scripts
OUTPUTS_DIR := $(ROOT)/outputs

.PHONY: validate scaffold validate-outputs clean help

help:
	@echo "Targets:"
	@echo "  make validate         Run scaffold generation then validate required outputs"
	@echo "  make scaffold         Run scaffold generation only"
	@echo "  make validate-outputs  Validate required outputs only"
	@echo "  make clean            Remove outputs directory"

validate: scaffold validate-outputs

scaffold:
	@test -f "$(SCRIPTS)/run_scaffold.py" || (echo "Missing: scripts/run_scaffold.py" >&2; exit 2)
	$(PYTHON) "$(SCRIPTS)/run_scaffold.py"

validate-outputs:
	@test -f "$(SCRIPTS)/validate_outputs.py" || (echo "Missing: scripts/validate_outputs.py" >&2; exit 2)
	$(PYTHON) "$(SCRIPTS)/validate_outputs.py" --outputs-dir "$(OUTPUTS_DIR)"

clean:
	rm -rf "$(OUTPUTS_DIR)"

# Makefile
# Purpose: Provide standard `make run` and `make test` targets that ALWAYS
# write logs to outputs/run.log and outputs/test.log (mandatory cycle artifacts).

SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c

# Override these as needed, e.g.:
#   make run RUN_CMD="python -m your_module"
#   make test TEST_CMD="python -m pytest -q"
RUN_CMD ?= python -m generated_script_1766543295064
TEST_CMD ?= python -m pytest -q

OUTPUTS_DIR := outputs
RUN_LOG := $(OUTPUTS_DIR)/run.log
TEST_LOG := $(OUTPUTS_DIR)/test.log

.PHONY: help run test clean-logs

help:
	@printf "%s\n" \
	  "Targets:" \
	  "  make run   - run the project; writes $(RUN_LOG)" \
	  "  make test  - run tests; writes $(TEST_LOG)" \
	  "" \
	  "Variables (override on CLI):" \
	  "  RUN_CMD=...   (default: $(RUN_CMD))" \
	  "  TEST_CMD=...  (default: $(TEST_CMD))"

$(OUTPUTS_DIR):
	@mkdir -p "$(OUTPUTS_DIR)"

run: $(OUTPUTS_DIR)
	@echo "=== make run @ $$(date -Iseconds) ===" | tee "$(RUN_LOG)"
	@echo "RUN_CMD: $(RUN_CMD)" | tee -a "$(RUN_LOG)"
	@{ $(RUN_CMD); } 2>&1 | tee -a "$(RUN_LOG)"

test: $(OUTPUTS_DIR)
	@echo "=== make test @ $$(date -Iseconds) ===" | tee "$(TEST_LOG)"
	@echo "TEST_CMD: $(TEST_CMD)" | tee -a "$(TEST_LOG)"
	@{ $(TEST_CMD); } 2>&1 | tee -a "$(TEST_LOG)"

clean-logs:
	@rm -f "$(RUN_LOG)" "$(TEST_LOG)"

SHELL := /bin/sh

.PHONY: help verify-artifacts verify verify-build-artifacts clean-verify

PY ?= python3
VERIFY_SCRIPT ?= scripts/verify_build_artifacts.py
VERIFY_CONFIG ?= scripts/verify_build_artifacts.json
BUILD_DIR ?= runtime/_build

help:
	@printf "%s\n" "Targets:"
	@printf "%s\n" "  verify-artifacts  Run deterministic build artifact verification (single-command entrypoint)"
	@printf "%s\n" "  verify            Alias for verify-artifacts"
	@printf "%s\n" "  clean-verify       Remove verifier cache/output (if any; safe no-op)"

verify: verify-artifacts
verify-build-artifacts: verify-artifacts

verify-artifacts:
	@$(PY) $(VERIFY_SCRIPT) --config $(VERIFY_CONFIG) --build-dir $(BUILD_DIR)

clean-verify:
	@rm -f .artifact_verify_cache.json .artifact_verify_cache.lock 2>/dev/null || true

"""Public API for the `overrides` package.

This module re-exports the schema, YAML helpers, example generator, and apply engine
so consumers can import from `overrides` directly.
"""

from __future__ import annotations
# Schema / validation
from .schema import (
    OVERRIDES_SCHEMA_VERSION,
    OverridesConfig,
    OverridesSchemaError,
    ValidationError,
    normalize_overrides_config,
    validate_overrides_config,
)
# YAML support
from .yaml_support import (
    OverridesYAMLError,
    dump_overrides_yaml,
    load_overrides_yaml,
)
# Example generator
from .overrides_example_yaml import (
    generate_example_overrides_yaml,
)
# Apply engine
from .apply import (
    ApplyOverridesError,
    apply_overrides,
)
__all__ = [
    # schema
    "OVERRIDES_SCHEMA_VERSION",
    "OverridesConfig",
    "OverridesSchemaError",
    "ValidationError",
    "normalize_overrides_config",
    "validate_overrides_config",
    # yaml
    "OverridesYAMLError",
    "dump_overrides_yaml",
    "load_overrides_yaml",
    # examples
    "generate_example_overrides_yaml",
    # apply
    "ApplyOverridesError",
    "apply_overrides",
]

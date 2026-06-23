"""Configuration loading utilities.

Loads product configs from config/products/{product}.yaml and
pipeline config from config/pipeline.yaml. Resolves paths relative
to the project root (parent of the pulse/ package).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _project_root() -> Path:
    """Return the project root directory (parent of pulse/)."""
    return Path(__file__).resolve().parent.parent


def load_product_config(product: str) -> dict[str, Any]:
    """Load a product configuration by slug.

    Args:
        product: Product slug, e.g. "groww".

    Returns:
        Parsed YAML dict from config/products/{product}.yaml.

    Raises:
        FileNotFoundError: If the product config file doesn't exist.
        yaml.YAMLError: If the YAML is malformed.
    """
    config_path = _project_root() / "config" / "products" / f"{product}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Product config not found: {config_path}"
        )
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_pipeline_config() -> dict[str, Any]:
    """Load the pipeline configuration.

    Returns:
        Parsed YAML dict from config/pipeline.yaml.

    Raises:
        FileNotFoundError: If the pipeline config file doesn't exist.
        yaml.YAMLError: If the YAML is malformed.
    """
    config_path = _project_root() / "config" / "pipeline.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            f"Pipeline config not found: {config_path}"
        )
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def get_env_var(name: str, required: bool = True, default: str | None = None) -> str | None:
    """Get an environment variable with optional enforcement.

    Args:
        name: Environment variable name.
        required: If True, raise if not set and no default.
        default: Default value if not set.

    Returns:
        The env var value, or default.

    Raises:
        EnvironmentError: If required and not set.
    """
    value = os.environ.get(name, default)
    if required and value is None:
        raise EnvironmentError(f"Missing required env var: {name}")
    return value

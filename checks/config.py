from __future__ import annotations
"""
Configuration loader — reads check definitions from YAML/JSON files.

Users define their checks in config files rather than writing code.
A check definition is just:
  - Which connector to talk to
  - Which evaluator to run
  - What config to pass (account IDs, thresholds, exclusions, etc.)

Config can be loaded from:
  1. A checks.yml file in the working directory
  2. ~/.checks/checks.yml (user-level config)
  3. Environment variable CHECKS_CONFIG_PATH pointing to a file
  4. Programmatically via load_config()

Example checks.yml:
  checks:
    mfa_enforced:
      connector: okta
      evaluator: mfa_enforced
      config:
        exclude_users: ["service-bot@company.com"]

    branch_protection:
      connector: github
      evaluator: branch_protection
      config:
        critical_repos: ["company/api", "company/frontend"]
        min_required_reviews: 2

    s3_encryption:
      connector: aws
      evaluator: s3_encryption
      config:
        exclude_buckets: ["temp-scratch-bucket"]

    key_rotation:
      connector: aws
      evaluator: access_key_rotation
      config:
        max_key_age_days: 90
"""

import os
from pathlib import Path
from typing import Any

import yaml

from .decision import CheckCatalog, RetrievalCatalog

CONFIG_SEARCH_PATHS = [
    Path("checks.yml"),
    Path("checks.yaml"),
    Path.home() / ".checks" / "checks.yml",
]


def find_config_path() -> Path | None:
    """Find the first available config file."""
    # Explicit env var takes priority
    env_path = os.environ.get("CHECKS_CONFIG_PATH")
    if env_path:
        p = Path(env_path)
        if p.exists():
            return p

    # Search standard locations
    for path in CONFIG_SEARCH_PATHS:
        if path.exists():
            return path

    return None


def load_config(path: str | Path | None = None) -> dict:
    """Load check configuration from a YAML file.

    Returns the full config dict with keys:
      - checks: dict of check definitions
      - retrievals: dict of retrieval definitions (optional)
      - settings: global settings (optional)
    """
    if path is None:
        path = find_config_path()

    if path is None:
        return {"checks": {}, "retrievals": {}, "settings": {}}

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = yaml.safe_load(path.read_text()) or {}

    return {
        "checks": data.get("checks", {}),
        "retrievals": data.get("retrievals", {}),
        "settings": data.get("settings", {}),
    }


def build_catalogs(config: dict) -> tuple[CheckCatalog, RetrievalCatalog]:
    """Build check and retrieval catalogs from loaded config."""
    check_catalog = CheckCatalog(checks={
        key: {"key": key, **defn}
        for key, defn in config.get("checks", {}).items()
    })

    retrieval_catalog = RetrievalCatalog(retrievals={
        key: {"key": key, **defn}
        for key, defn in config.get("retrievals", {}).items()
    })

    return check_catalog, retrieval_catalog


def validate_config(config: dict) -> list[str]:
    """Validate a config dict. Returns list of error messages (empty = valid)."""
    from .connectors import list_connectors
    from .evaluators import list_evaluators

    errors = []
    valid_connectors = set(list_connectors().keys())
    valid_evaluators = set(list_evaluators().keys())

    for key, defn in config.get("checks", {}).items():
        if "connector" not in defn:
            errors.append(f"Check '{key}': missing 'connector' field")
        elif defn["connector"] not in valid_connectors:
            errors.append(f"Check '{key}': unknown connector '{defn['connector']}'. Valid: {sorted(valid_connectors)}")

        if "evaluator" not in defn:
            errors.append(f"Check '{key}': missing 'evaluator' field")
        elif defn["evaluator"] not in valid_evaluators:
            errors.append(f"Check '{key}': unknown evaluator '{defn['evaluator']}'. Valid: {sorted(valid_evaluators)}")

    return errors

from __future__ import annotations
"""
Check runner — executes a check definition and returns a CheckResult.

This is the core primitive both OCULUS and EXHIBIT consume:
  - OCULUS calls run_check() on a schedule
  - EXHIBIT calls run_check() when it needs fresh evidence
  - Both get back the same CheckResult with structured evidence

A "check definition" is just config:
  {
      "key": "mfa_enforced",
      "connector": "okta",
      "evaluator": "mfa_enforced",
      "config": {"exclude_users": ["service-account@company.com"]}
  }

That's it. No code needed to define a new check — just config.
"""

import time
from datetime import datetime, timezone

from .connectors import get_connector
from .evaluators import get_evaluator
from .models import CheckResult, Status


def run_check(
    connector_type: str,
    evaluator_type: str,
    config: dict | None = None,
    force_real: bool = False,
) -> CheckResult:
    """Execute a single check: connector.fetch() → evaluator.evaluate() → CheckResult.

    Args:
        connector_type: Which connector to use (e.g., "okta", "aws", "github")
        evaluator_type: Which evaluator to run (e.g., "mfa_enforced", "s3_encryption")
        config: Check-specific config (thresholds, filters, account lists, etc.)
        force_real: If True, fail rather than use mock data when credentials are missing

    Returns:
        CheckResult with status, summary, evidence, and failures.
    """
    config = config or {}
    start = time.monotonic()

    try:
        connector = get_connector(connector_type, force_real=force_real)
        data = connector.fetch(config)
    except Exception as e:
        return CheckResult(
            status=Status.ERROR,
            summary=f"Connector '{connector_type}' failed: {e}",
            connector_type=connector_type,
            evaluator_type=evaluator_type,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    try:
        eval_instance = get_evaluator(evaluator_type)
        result = eval_instance.evaluate(data, config)
    except Exception as e:
        return CheckResult(
            status=Status.ERROR,
            summary=f"Evaluator '{evaluator_type}' failed: {e}",
            connector_type=connector_type,
            evaluator_type=evaluator_type,
            duration_ms=int((time.monotonic() - start) * 1000),
        )

    # Enrich result with execution metadata
    result.connector_type = connector_type
    result.evaluator_type = evaluator_type
    result.duration_ms = int((time.monotonic() - start) * 1000)
    result.executed_at = datetime.now(timezone.utc).isoformat()
    return result


def run_check_from_definition(definition: dict, force_real: bool = False) -> CheckResult:
    """Run a check from a definition dict (as stored in config files).

    Definition format:
        {
            "key": "mfa_enforced",          # unique identifier
            "connector": "okta",             # connector type
            "evaluator": "mfa_enforced",     # evaluator type
            "config": {...}                  # check-specific config
        }
    """
    result = run_check(
        connector_type=definition["connector"],
        evaluator_type=definition["evaluator"],
        config=definition.get("config", {}),
        force_real=force_real,
    )
    result.check_key = definition.get("key", "")
    return result

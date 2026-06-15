"""
CHECKS — Shared compliance check library.

A portable, config-driven package for deterministic security control
evaluation. Drop it into any environment, point it at your systems,
and get pass/fail + structured evidence.

Used by:
  - OCULUS (continuous monitoring — runs checks on a schedule)
  - EXHIBIT (audit response — pulls check results as evidence)

Design principles:
  - Checks are data, not code. Define what to check in YAML/JSON config.
  - Evaluators are pure functions. No side effects, no API calls.
  - Connectors handle all I/O. One connector per system.
  - Everything returns structured evidence alongside pass/fail.
  - Mock data built in for every connector (dev/test without credentials).
  - Decision engine routes: check → retrieval → agent (cheapest first).
"""

__version__ = "0.1.0"

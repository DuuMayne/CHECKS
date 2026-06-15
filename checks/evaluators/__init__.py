"""
Evaluator registry — pure deterministic functions that take data and return pass/fail.

Import this module to populate the registry. Individual evaluators
self-register via the @evaluator decorator.
"""

# Import all built-in evaluators to trigger registration
from . import (
    access_keys,  # noqa: F401
    branch_protection,  # noqa: F401
    cloudtrail,  # noqa: F401
    encryption,  # noqa: F401
    mfa,  # noqa: F401
)
from .base import EvaluatorBase, evaluator, get_evaluator, list_evaluators

__all__ = ["EvaluatorBase", "evaluator", "get_evaluator", "list_evaluators"]

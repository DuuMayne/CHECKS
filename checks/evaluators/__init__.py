"""
Evaluator registry — pure deterministic functions that take data and return pass/fail.

Import this module to populate the registry. Individual evaluators
self-register via the @evaluator decorator.
"""
from .base import EvaluatorBase, evaluator, get_evaluator, list_evaluators

# Import all built-in evaluators to trigger registration
from . import mfa  # noqa: F401
from . import branch_protection  # noqa: F401
from . import encryption  # noqa: F401
from . import access_keys  # noqa: F401
from . import cloudtrail  # noqa: F401

__all__ = ["EvaluatorBase", "evaluator", "get_evaluator", "list_evaluators"]

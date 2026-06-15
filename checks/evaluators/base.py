from __future__ import annotations

"""
Evaluator base class and registry.

Evaluators are pure functions: they receive normalized data from a connector
and return a CheckResult. They never make API calls, never have side effects,
and are trivially testable.

The separation is intentional:
  - Connector: "Get me the data" (I/O, pagination, auth)
  - Evaluator: "Is this data compliant?" (logic, thresholds, pass/fail)

This means you can:
  - Test evaluators with fixture data (no credentials needed)
  - Swap connectors without changing evaluators
  - Run the same evaluator against different systems
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from ..models import CheckResult

_REGISTRY: dict[str, type[EvaluatorBase]] = {}


class EvaluatorBase(ABC):
    """Base class for all control evaluators.

    Subclasses must define:
      - evaluator_type: unique string identifier (e.g., "mfa_enforced")
      - description: what this evaluator checks
      - evaluate(): the actual pass/fail logic
    """

    evaluator_type: ClassVar[str] = ""
    description: ClassVar[str] = ""

    @abstractmethod
    def evaluate(self, data: dict, config: dict) -> CheckResult:
        """Evaluate data against the control criteria.

        Args:
            data: Normalized dict from a connector's fetch() output.
            config: Check-specific configuration (thresholds, filters, etc.)

        Returns:
            CheckResult with status, summary, evidence, and failures.
        """
        ...


def evaluator(cls: type[EvaluatorBase]) -> type[EvaluatorBase]:
    """Decorator to register an evaluator class."""
    if cls.evaluator_type:
        _REGISTRY[cls.evaluator_type] = cls
    return cls


def get_evaluator(evaluator_type: str) -> EvaluatorBase:
    """Get an evaluator instance by type."""
    cls = _REGISTRY.get(evaluator_type)
    if cls is None:
        raise ValueError(f"Unknown evaluator type: '{evaluator_type}'. Available: {list(_REGISTRY.keys())}")
    return cls()


def list_evaluators() -> dict[str, str]:
    """List all registered evaluators and their descriptions."""
    return {name: cls.description for name, cls in _REGISTRY.items()}

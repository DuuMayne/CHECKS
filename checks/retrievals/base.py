"""
Retrieval base class and registry.

Retrievals fetch specific artifacts from systems with known parameters.
Unlike evaluators, they don't judge pass/fail — they just get the thing.

Examples:
  - "All Jira tickets labeled 'access-review' from Q1 2026"
  - "Okta user list with MFA status and last login"
  - "GitHub PRs merged to main in the last 90 days"
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from ..models import RetrievalResult

_REGISTRY: dict[str, type[RetrievalBase]] = {}


class RetrievalBase(ABC):
    """Base class for parameterized artifact retrieval.

    Subclasses must define:
      - retrieval_type: unique string identifier
      - system: which connector's system this retrieves from
      - description: what artifact this fetches
      - fetch(): the actual retrieval logic
    """

    retrieval_type: ClassVar[str] = ""
    system: ClassVar[str] = ""
    description: ClassVar[str] = ""

    @abstractmethod
    def fetch(self, params: dict) -> RetrievalResult:
        """Fetch the artifact with given parameters.

        Args:
            params: Retrieval-specific parameters (date ranges, filters, etc.)

        Returns:
            RetrievalResult with the artifact data.
        """
        ...


def retrieval(cls: type[RetrievalBase]) -> type[RetrievalBase]:
    """Decorator to register a retrieval class."""
    if cls.retrieval_type:
        _REGISTRY[cls.retrieval_type] = cls
    return cls


def get_retrieval(retrieval_type: str) -> RetrievalBase:
    """Get a retrieval instance by type."""
    cls = _REGISTRY.get(retrieval_type)
    if cls is None:
        raise ValueError(
            f"Unknown retrieval type: '{retrieval_type}'. "
            f"Available: {list(_REGISTRY.keys())}"
        )
    return cls()


def list_retrievals() -> dict[str, dict]:
    """List all registered retrievals."""
    return {
        name: {"system": cls.system, "description": cls.description}
        for name, cls in _REGISTRY.items()
    }

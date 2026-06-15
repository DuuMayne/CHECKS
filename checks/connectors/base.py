from __future__ import annotations

"""
Connector base class and registry.

Connectors handle all external I/O — API calls, credential management,
pagination, rate limiting. They return normalized dicts that evaluators
consume without knowing anything about the source system's API.

Key design choices:
- Connectors declare their required env vars upfront
- If credentials aren't present, mock data is returned automatically
- Every connector ships with realistic mock data for dev/test
- Connectors are stateless between fetch() calls (can be re-instantiated)
"""

import os
from abc import ABC, abstractmethod
from typing import ClassVar

_REGISTRY: dict[str, type[ConnectorBase]] = {}


class ConnectorBase(ABC):
    """Base class for all system connectors.

    Subclasses must define:
      - connector_type: unique string identifier (e.g., "okta")
      - required_env: list of env vars needed for real operation
      - mock_data: realistic fixture data for dev/testing
      - fetch(): actual data retrieval logic
      - test_connection(): credential validation
    """

    connector_type: ClassVar[str] = ""
    required_env: ClassVar[list[str]] = []
    mock_data: ClassVar[dict] = {}

    @abstractmethod
    def fetch(self, config: dict) -> dict:
        """Fetch data from the external system.

        Args:
            config: Check-specific configuration (e.g., which repos to check,
                    which accounts to scan, threshold values).

        Returns:
            Normalized dict in the format evaluators expect.
        """
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify credentials work. Returns True if connected."""
        ...

    @classmethod
    def is_configured(cls) -> bool:
        """Check if all required environment variables are set."""
        return all(os.environ.get(var) for var in cls.required_env)


class MockConnector(ConnectorBase):
    """Fallback connector that returns static mock data."""

    connector_type = "_mock"
    required_env = []

    def __init__(self, data: dict):
        self._data = data

    def fetch(self, config: dict) -> dict:
        return self._data

    def test_connection(self) -> bool:
        return True


def connector(cls: type[ConnectorBase]) -> type[ConnectorBase]:
    """Decorator to register a connector class."""
    if cls.connector_type:
        _REGISTRY[cls.connector_type] = cls
    return cls


def get_connector(connector_type: str, force_real: bool = False) -> ConnectorBase:
    """Get a connector instance. Returns mock if credentials aren't configured.

    Args:
        connector_type: The connector identifier (e.g., "okta")
        force_real: If True, raises ValueError when credentials are missing
                    instead of falling back to mock.
    """
    cls = _REGISTRY.get(connector_type)
    if cls is None:
        raise ValueError(f"Unknown connector type: '{connector_type}'. Available: {list(_REGISTRY.keys())}")

    if cls.is_configured():
        return cls()

    if force_real:
        missing = [v for v in cls.required_env if not os.environ.get(v)]
        raise ValueError(f"Connector '{connector_type}' requires env vars: {missing}")

    return MockConnector(cls.mock_data)


def list_connectors() -> dict[str, dict]:
    """List all registered connectors and their configuration status."""
    result = {}
    for name, cls in _REGISTRY.items():
        result[name] = {
            "configured": cls.is_configured(),
            "required_env": cls.required_env,
            "has_mock": bool(cls.mock_data),
        }
    return result

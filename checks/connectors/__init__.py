"""
Connector registry — auto-discovers and registers all connector implementations.

Import this module to populate the registry. Individual connectors
self-register via the @connector decorator.
"""

# Import all built-in connectors to trigger registration
from . import (
    aws,  # noqa: F401
    github,  # noqa: F401
    okta,  # noqa: F401
)
from .base import ConnectorBase, connector, get_connector, list_connectors

__all__ = ["ConnectorBase", "connector", "get_connector", "list_connectors"]

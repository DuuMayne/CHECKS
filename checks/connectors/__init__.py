"""
Connector registry — auto-discovers and registers all connector implementations.

Import this module to populate the registry. Individual connectors
self-register via the @connector decorator.
"""
from .base import ConnectorBase, connector, get_connector, list_connectors

# Import all built-in connectors to trigger registration
from . import okta  # noqa: F401
from . import github  # noqa: F401
from . import aws  # noqa: F401

__all__ = ["ConnectorBase", "connector", "get_connector", "list_connectors"]

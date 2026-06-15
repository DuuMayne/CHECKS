"""
Retrieval registry — parameterized artifact fetchers.

Retrievals are the middle tier: not a binary pass/fail check, but a known
artifact type with known parameters. "Get me the Jira tickets with label
X from the last 90 days" is a retrieval — deterministic, no LLM needed.
"""

from .base import RetrievalBase, get_retrieval, list_retrievals, retrieval

__all__ = ["RetrievalBase", "get_retrieval", "list_retrievals", "retrieval"]

from __future__ import annotations

"""
Core data models for the checks library.

These are the primitives that all checks produce and all consumers
(OCULUS, EXHIBIT, etc.) understand.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Status(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


@dataclass
class FailingResource:
    """A single non-compliant resource identified during evaluation."""

    resource_type: str  # e.g., "user", "repository", "s3_bucket"
    resource_id: str  # e.g., "alice@company.com", "org/repo"
    reason: str  # Human-readable: "MFA not enrolled"
    details: dict = field(default_factory=dict)  # Arbitrary structured context


@dataclass
class CheckResult:
    """The output of running a check. Contains everything needed for both
    monitoring (OCULUS) and audit evidence (EXHIBIT)."""

    status: Status
    summary: str  # Human-readable: "3 of 42 users lack MFA"

    # Structured evidence — the raw proof
    evidence: dict = field(default_factory=dict)

    # Individual failing resources (empty on pass)
    failures: list[FailingResource] = field(default_factory=list)

    # Metadata about the check execution
    check_key: str = ""
    connector_type: str = ""
    evaluator_type: str = ""
    executed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: int = 0

    @property
    def passed(self) -> bool:
        return self.status == Status.PASS


@dataclass
class RetrievalResult:
    """The output of a retrieval operation — fetching a specific artifact."""

    artifact_type: str  # e.g., "user_list", "pr_history", "policy_document"
    system: str  # e.g., "okta", "github", "jira"
    data: Any = None  # The actual artifact (dict, list, bytes, etc.)
    description: str = ""  # What this artifact represents
    metadata: dict = field(default_factory=dict)
    error: str | None = None
    executed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class Tier(str, Enum):
    """Evidence collection tier — cheapest to most expensive."""

    CHECK = "check"  # Deterministic pass/fail, near-zero cost
    RETRIEVAL = "retrieval"  # Known artifact fetch, one API call
    AGENT = "agent"  # LLM reasoning required


@dataclass
class RoutingDecision:
    """The decision engine's output for a given evidence request."""

    tier: Tier
    reason: str  # Why this tier was chosen

    # Populated based on tier:
    check_keys: list[str] = field(default_factory=list)  # Tier.CHECK
    retrieval_specs: list[dict] = field(default_factory=list)  # Tier.RETRIEVAL
    # Tier.AGENT — nothing pre-determined, agent figures it out

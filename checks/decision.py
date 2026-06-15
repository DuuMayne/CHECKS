from __future__ import annotations

"""
Decision engine — routes evidence requests to the cheapest tier.

Given an evidence request (question + context), determines whether it can be
answered by:
  1. A deterministic check (Tier 1 — near-zero cost)
  2. A parameterized retrieval (Tier 2 — one API call)
  3. An agent (Tier 3 — LLM reasoning, expensive)

The engine consults:
  - The check catalog (what checks are defined and available)
  - The retrieval catalog (what artifacts can be fetched with known params)
  - Pattern matching on the question text (as a fallback heuristic)

This keeps LLM usage to a minimum — only for genuinely ambiguous requests.
"""

import re
from dataclasses import dataclass, field

from .models import RoutingDecision, Tier

# Patterns that indicate a Tier 1 (check) question
CHECK_PATTERNS = [
    r"is .* enabled",
    r"are all .* (encrypted|protected|configured|enforced|enrolled)",
    r"do all .* have",
    r"is .* (active|running|logging)",
    r"(enforce|require) .* (mfa|multi-factor|2fa|encryption|protection)",
    r"(compliant|compliance) with",
]

# Patterns that indicate a Tier 2 (retrieval) question
RETRIEVAL_PATTERNS = [
    r"provide (a |the )?(list|inventory|export|report|sample)",
    r"provide evidence of",
    r"show .* (configuration|settings|policy)",
    r"(list|export) .* (users|accounts|repos|tickets|keys)",
    r"(sample|population) of .* (tickets|changes|reviews|requests)",
    r"provide .* (from|during|for) .* (q[1-4]|last|past|period)",
]

# Patterns that indicate Tier 3 (agent) — complex reasoning
AGENT_PATTERNS = [
    r"demonstrate (that|how|effectiveness)",
    r"describe .* process",
    r"explain how",
    r"provide evidence .* operating effectively",
    r"show how .* (manages|handles|responds|ensures)",
]


@dataclass
class CheckCatalog:
    """Registry of available check definitions, keyed by check_key."""

    checks: dict[str, dict] = field(default_factory=dict)

    def find_checks_for(self, systems: list[str], keywords: list[str]) -> list[str]:
        """Find check keys relevant to given systems and keywords."""
        matches = []
        for key, defn in self.checks.items():
            if defn.get("connector") in systems:
                matches.append(key)
            elif any(kw in key for kw in keywords):
                matches.append(key)
        return matches


@dataclass
class RetrievalCatalog:
    """Registry of available retrieval definitions."""

    retrievals: dict[str, dict] = field(default_factory=dict)

    def find_retrievals_for(self, systems: list[str], artifact_type: str | None = None) -> list[dict]:
        """Find retrieval specs relevant to given systems."""
        matches = []
        for _key, spec in self.retrievals.items():
            if spec.get("system") in systems:
                if artifact_type is None or spec.get("artifact_type") == artifact_type:
                    matches.append(spec)
        return matches


def route(
    question: str,
    systems: list[str],
    check_catalog: CheckCatalog | None = None,
    retrieval_catalog: RetrievalCatalog | None = None,
) -> RoutingDecision:
    """Determine the cheapest evidence tier for a given question.

    Args:
        question: The audit question or evidence request text.
        systems: Systems this question is mapped to (e.g., ["okta", "aws"]).
        check_catalog: Available checks (from config). If None, uses pattern matching only.
        retrieval_catalog: Available retrievals (from config). If None, uses pattern matching only.

    Returns:
        RoutingDecision with the tier and relevant check/retrieval specs.
    """
    q_lower = question.lower()

    # --- Tier 1: Check ---
    # First: see if we have explicit checks defined for these systems
    if check_catalog:
        keywords = _extract_keywords(q_lower)
        matching_checks = check_catalog.find_checks_for(systems, keywords)
        if matching_checks:
            return RoutingDecision(
                tier=Tier.CHECK,
                reason=f"Deterministic checks available: {matching_checks}",
                check_keys=matching_checks,
            )

    # Fallback: pattern match for check-type questions
    if any(re.search(p, q_lower) for p in CHECK_PATTERNS):
        return RoutingDecision(
            tier=Tier.CHECK,
            reason="Question pattern matches deterministic check (no specific check defined yet)",
            check_keys=[],  # Consumer should still try to find/create a check
        )

    # --- Tier 2: Retrieval ---
    if retrieval_catalog:
        matching_retrievals = retrieval_catalog.find_retrievals_for(systems)
        if matching_retrievals and any(re.search(p, q_lower) for p in RETRIEVAL_PATTERNS):
            return RoutingDecision(
                tier=Tier.RETRIEVAL,
                reason=f"Retrieval patterns available for {systems}",
                retrieval_specs=matching_retrievals,
            )

    # Fallback: pattern match for retrieval-type questions
    if any(re.search(p, q_lower) for p in RETRIEVAL_PATTERNS):
        return RoutingDecision(
            tier=Tier.RETRIEVAL,
            reason="Question pattern matches artifact retrieval",
            retrieval_specs=[],
        )

    # --- Tier 3: Agent ---
    # Explicit agent patterns
    if any(re.search(p, q_lower) for p in AGENT_PATTERNS):
        return RoutingDecision(
            tier=Tier.AGENT,
            reason="Question requires qualitative reasoning or multi-artifact assembly",
        )

    # Default: if nothing matched, try retrieval first (cheaper than agent)
    return RoutingDecision(
        tier=Tier.RETRIEVAL,
        reason="No specific check or pattern matched; defaulting to retrieval attempt",
        retrieval_specs=[],
    )


def _extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords for check matching."""
    # Simple keyword extraction — pull out the meaningful terms
    stopwords = {
        "is",
        "are",
        "do",
        "does",
        "have",
        "has",
        "the",
        "a",
        "an",
        "all",
        "for",
        "to",
        "in",
        "on",
        "at",
        "from",
        "with",
        "that",
        "this",
        "provide",
        "evidence",
        "show",
        "your",
        "of",
        "and",
        "or",
    }
    words = re.findall(r"[a-z_]+", text)
    return [w for w in words if w not in stopwords and len(w) > 2]

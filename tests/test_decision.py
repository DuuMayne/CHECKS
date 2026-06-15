"""Tests for the decision engine — routing to cheapest tier."""

from checks.decision import CheckCatalog, route
from checks.models import Tier


class TestDecisionEngine:
    def test_check_pattern_detected(self):
        decision = route("Are all S3 buckets encrypted at rest?", ["aws"])
        assert decision.tier == Tier.CHECK

    def test_retrieval_pattern_detected(self):
        decision = route("Provide a list of all users with their MFA status", ["okta"])
        assert decision.tier == Tier.RETRIEVAL

    def test_agent_pattern_detected(self):
        decision = route(
            "Demonstrate that your incident response process is operating effectively",
            ["jira", "confluence"],
        )
        assert decision.tier == Tier.AGENT

    def test_catalog_match_overrides_pattern(self):
        catalog = CheckCatalog(
            checks={
                "mfa_enforced": {"key": "mfa_enforced", "connector": "okta", "evaluator": "mfa_enforced"},
            }
        )
        decision = route("Provide evidence of MFA enforcement", ["okta"], check_catalog=catalog)
        assert decision.tier == Tier.CHECK
        assert "mfa_enforced" in decision.check_keys

    def test_unknown_defaults_to_retrieval(self):
        decision = route("Something generic about security posture", ["aws"])
        assert decision.tier == Tier.RETRIEVAL
        assert "default" in decision.reason.lower() or "pattern" in decision.reason.lower()

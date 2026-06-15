"""Tests for the runner — end-to-end check execution with mock data."""

from checks.models import Status
from checks.runner import run_check, run_check_from_definition


class TestRunCheck:
    def test_okta_mfa_with_mock(self):
        """Running with no credentials should use mock data and produce results."""
        result = run_check("okta", "mfa_enforced", {})
        assert result.status in (Status.PASS, Status.FAIL)
        assert result.summary
        assert result.evidence
        assert result.connector_type == "okta"
        assert result.evaluator_type == "mfa_enforced"
        assert result.duration_ms >= 0

    def test_github_branch_protection_with_mock(self):
        result = run_check("github", "branch_protection", {})
        assert result.status in (Status.PASS, Status.FAIL)
        assert "repos" in result.summary.lower()

    def test_aws_s3_encryption_with_mock(self):
        result = run_check("aws", "s3_encryption", {})
        assert result.status in (Status.PASS, Status.FAIL)
        assert result.evidence.get("total_buckets", 0) > 0

    def test_unknown_connector_raises(self):
        result = run_check("nonexistent", "mfa_enforced", {})
        assert result.status == Status.ERROR
        assert "nonexistent" in result.summary.lower()

    def test_unknown_evaluator_raises(self):
        result = run_check("okta", "nonexistent_evaluator", {})
        assert result.status == Status.ERROR
        assert "nonexistent" in result.summary.lower()


class TestRunFromDefinition:
    def test_basic_definition(self):
        defn = {
            "key": "test_mfa",
            "connector": "okta",
            "evaluator": "mfa_enforced",
            "config": {"exclude_users": ["service-bot@company.com"]},
        }
        result = run_check_from_definition(defn)
        assert result.check_key == "test_mfa"
        assert result.status in (Status.PASS, Status.FAIL)

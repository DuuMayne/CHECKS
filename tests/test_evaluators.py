"""Tests for evaluators — each evaluator is a pure function, trivially testable."""

from checks.evaluators.access_keys import AccessKeyRotationEvaluator
from checks.evaluators.branch_protection import BranchProtectionEvaluator
from checks.evaluators.cloudtrail import CloudTrailEnabledEvaluator
from checks.evaluators.encryption import S3EncryptionEvaluator
from checks.evaluators.mfa import MfaEnforcedEvaluator
from checks.models import Status


class TestMfaEnforced:
    def test_all_pass(self):
        data = {
            "users": [
                {"id": "u1", "email": "a@co.com", "status": "ACTIVE", "mfa_enrolled": True, "mfa_factors": ["push"]},
                {"id": "u2", "email": "b@co.com", "status": "ACTIVE", "mfa_enrolled": True, "mfa_factors": ["sms"]},
            ]
        }
        result = MfaEnforcedEvaluator().evaluate(data, {})
        assert result.status == Status.PASS
        assert result.failures == []
        assert result.evidence["compliance_rate"] == 1.0

    def test_some_fail(self):
        data = {
            "users": [
                {"id": "u1", "email": "good@co.com", "status": "ACTIVE", "mfa_enrolled": True, "mfa_factors": ["push"]},
                {"id": "u2", "email": "bad@co.com", "status": "ACTIVE", "mfa_enrolled": False, "mfa_factors": []},
            ]
        }
        result = MfaEnforcedEvaluator().evaluate(data, {})
        assert result.status == Status.FAIL
        assert len(result.failures) == 1
        assert result.failures[0].resource_id == "bad@co.com"

    def test_excludes_inactive(self):
        data = {
            "users": [
                {
                    "id": "u1",
                    "email": "active@co.com",
                    "status": "ACTIVE",
                    "mfa_enrolled": True,
                    "mfa_factors": ["push"],
                },
                {
                    "id": "u2",
                    "email": "gone@co.com",
                    "status": "DEPROVISIONED",
                    "mfa_enrolled": False,
                    "mfa_factors": [],
                },
            ]
        }
        result = MfaEnforcedEvaluator().evaluate(data, {})
        assert result.status == Status.PASS
        assert result.evidence["active_users"] == 1

    def test_exclude_users_config(self):
        data = {
            "users": [
                {
                    "id": "u1",
                    "email": "human@co.com",
                    "status": "ACTIVE",
                    "mfa_enrolled": True,
                    "mfa_factors": ["push"],
                },
                {"id": "u2", "email": "bot@co.com", "status": "ACTIVE", "mfa_enrolled": False, "mfa_factors": []},
            ]
        }
        result = MfaEnforcedEvaluator().evaluate(data, {"exclude_users": ["bot@co.com"]})
        assert result.status == Status.PASS

    def test_empty_data_returns_error(self):
        result = MfaEnforcedEvaluator().evaluate({"users": []}, {})
        assert result.status == Status.ERROR


class TestBranchProtection:
    def test_all_protected(self):
        data = {
            "repos": [
                {
                    "full_name": "co/api",
                    "default_branch": "main",
                    "branch_protection": {"enabled": True, "required_reviews": 2},
                },
                {
                    "full_name": "co/web",
                    "default_branch": "main",
                    "branch_protection": {"enabled": True, "required_reviews": 1},
                },
            ]
        }
        result = BranchProtectionEvaluator().evaluate(data, {})
        assert result.status == Status.PASS

    def test_unprotected_repo(self):
        data = {
            "repos": [
                {
                    "full_name": "co/api",
                    "default_branch": "main",
                    "branch_protection": {"enabled": True, "required_reviews": 1},
                },
                {"full_name": "co/scripts", "default_branch": "main", "branch_protection": None},
            ]
        }
        result = BranchProtectionEvaluator().evaluate(data, {})
        assert result.status == Status.FAIL
        assert len(result.failures) == 1
        assert result.failures[0].resource_id == "co/scripts"

    def test_insufficient_reviews(self):
        data = {
            "repos": [
                {
                    "full_name": "co/api",
                    "default_branch": "main",
                    "branch_protection": {"enabled": True, "required_reviews": 1},
                },
            ]
        }
        result = BranchProtectionEvaluator().evaluate(data, {"min_required_reviews": 2})
        assert result.status == Status.FAIL
        assert "reviews" in result.failures[0].reason.lower()


class TestS3Encryption:
    def test_all_encrypted(self):
        data = {
            "buckets": [
                {"name": "prod-data", "encryption_enabled": True, "encryption_algorithm": "AES256"},
                {"name": "logs", "encryption_enabled": True, "encryption_algorithm": "aws:kms"},
            ]
        }
        result = S3EncryptionEvaluator().evaluate(data, {})
        assert result.status == Status.PASS

    def test_unencrypted_bucket(self):
        data = {
            "buckets": [
                {"name": "prod-data", "encryption_enabled": True},
                {"name": "temp", "encryption_enabled": False},
            ]
        }
        result = S3EncryptionEvaluator().evaluate(data, {})
        assert result.status == Status.FAIL
        assert result.failures[0].resource_id == "temp"

    def test_exclude_buckets(self):
        data = {
            "buckets": [
                {"name": "prod-data", "encryption_enabled": True},
                {"name": "scratch", "encryption_enabled": False},
            ]
        }
        result = S3EncryptionEvaluator().evaluate(data, {"exclude_buckets": ["scratch"]})
        assert result.status == Status.PASS


class TestAccessKeyRotation:
    def test_all_within_threshold(self):
        data = {
            "access_keys": [
                {"user_name": "deploy", "access_key_id": "AKIA1", "status": "Active", "age_days": 30},
                {"user_name": "ci", "access_key_id": "AKIA2", "status": "Active", "age_days": 60},
            ]
        }
        result = AccessKeyRotationEvaluator().evaluate(data, {"max_key_age_days": 90})
        assert result.status == Status.PASS

    def test_stale_key(self):
        data = {
            "access_keys": [
                {"user_name": "deploy", "access_key_id": "AKIA1", "status": "Active", "age_days": 120},
            ]
        }
        result = AccessKeyRotationEvaluator().evaluate(data, {"max_key_age_days": 90})
        assert result.status == Status.FAIL
        assert "120" in result.failures[0].reason

    def test_inactive_keys_ignored(self):
        data = {
            "access_keys": [
                {"user_name": "old", "access_key_id": "AKIA1", "status": "Inactive", "age_days": 500},
            ]
        }
        result = AccessKeyRotationEvaluator().evaluate(data, {"max_key_age_days": 90})
        assert result.status == Status.PASS


class TestCloudTrail:
    def test_all_logging(self):
        data = {
            "accounts": [
                {"account_id": "111", "account_name": "prod", "cloudtrail_enabled": True, "is_logging": True},
            ]
        }
        result = CloudTrailEnabledEvaluator().evaluate(data, {})
        assert result.status == Status.PASS

    def test_not_logging(self):
        data = {
            "accounts": [
                {"account_id": "111", "account_name": "prod", "cloudtrail_enabled": True, "is_logging": False},
            ]
        }
        result = CloudTrailEnabledEvaluator().evaluate(data, {})
        assert result.status == Status.FAIL
        assert result.failures[0].resource_id == "111"

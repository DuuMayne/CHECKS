"""CloudTrail evaluator — checks that audit logging is active in all accounts."""
from .base import EvaluatorBase, evaluator
from ..models import CheckResult, FailingResource, Status


@evaluator
class CloudTrailEnabledEvaluator(EvaluatorBase):
    evaluator_type = "cloudtrail_enabled"
    description = "All production accounts must have CloudTrail actively logging"

    def evaluate(self, data: dict, config: dict) -> CheckResult:
        accounts = data.get("accounts", [])
        if not accounts:
            return CheckResult(
                status=Status.ERROR,
                summary="No account data returned from connector",
                evaluator_type=self.evaluator_type,
            )

        non_compliant = [a for a in accounts if not a.get("is_logging")]

        failures = [
            FailingResource(
                resource_type="aws_account",
                resource_id=a.get("account_id", "unknown"),
                reason="CloudTrail not actively logging" if a.get("cloudtrail_enabled") else "No CloudTrail trail configured",
                details={
                    "account_name": a.get("account_name"),
                    "cloudtrail_enabled": a.get("cloudtrail_enabled"),
                    "is_logging": a.get("is_logging"),
                    "trail_name": a.get("trail_name"),
                    "error": a.get("error"),
                },
            )
            for a in non_compliant
        ]

        evidence = {
            "total_accounts": len(accounts),
            "logging_active": len(accounts) - len(non_compliant),
            "not_logging": len(non_compliant),
            "account_details": [
                {
                    "account_id": a.get("account_id"),
                    "account_name": a.get("account_name"),
                    "is_logging": a.get("is_logging", False),
                    "trail_name": a.get("trail_name"),
                }
                for a in accounts
            ],
        }

        if non_compliant:
            return CheckResult(
                status=Status.FAIL,
                summary=f"{len(non_compliant)} of {len(accounts)} accounts lack active CloudTrail logging",
                evidence=evidence,
                failures=failures,
                evaluator_type=self.evaluator_type,
            )

        return CheckResult(
            status=Status.PASS,
            summary=f"All {len(accounts)} accounts have CloudTrail actively logging",
            evidence=evidence,
            evaluator_type=self.evaluator_type,
        )

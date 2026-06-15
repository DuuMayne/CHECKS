"""Access key rotation evaluator — checks that no active keys exceed age threshold."""

from ..models import CheckResult, FailingResource, Status
from .base import EvaluatorBase, evaluator


@evaluator
class AccessKeyRotationEvaluator(EvaluatorBase):
    evaluator_type = "access_key_rotation"
    description = "All active IAM access keys must be rotated within the configured threshold"

    def evaluate(self, data: dict, config: dict) -> CheckResult:
        keys = data.get("access_keys", [])
        if keys is None:
            return CheckResult(
                status=Status.ERROR,
                summary="No access key data returned from connector",
                evaluator_type=self.evaluator_type,
            )

        max_age = config.get("max_key_age_days", 90)
        active_keys = [k for k in keys if k.get("status") == "Active"]

        stale = [k for k in active_keys if k.get("age_days", 0) > max_age]

        failures = [
            FailingResource(
                resource_type="access_key",
                resource_id=f"{k['user_name']}/{k['access_key_id']}",
                reason=f"Key is {k['age_days']} days old (max: {max_age})",
                details={
                    "user_name": k["user_name"],
                    "access_key_id": k["access_key_id"],
                    "age_days": k["age_days"],
                    "last_used": k.get("last_used"),
                },
            )
            for k in stale
        ]

        evidence = {
            "total_active_keys": len(active_keys),
            "compliant_keys": len(active_keys) - len(stale),
            "stale_keys": len(stale),
            "max_key_age_days": max_age,
            "stale_key_details": [
                {"user": k["user_name"], "key_id": k["access_key_id"], "age_days": k["age_days"]} for k in stale
            ],
        }

        if stale:
            return CheckResult(
                status=Status.FAIL,
                summary=f"{len(stale)} active access keys exceed {max_age}-day rotation threshold",
                evidence=evidence,
                failures=failures,
                evaluator_type=self.evaluator_type,
            )

        return CheckResult(
            status=Status.PASS,
            summary=f"All {len(active_keys)} active access keys are within {max_age}-day rotation threshold",
            evidence=evidence,
            evaluator_type=self.evaluator_type,
        )

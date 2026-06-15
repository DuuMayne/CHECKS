"""MFA enforcement evaluator — checks that all active users have MFA enrolled."""

from ..models import CheckResult, FailingResource, Status
from .base import EvaluatorBase, evaluator


@evaluator
class MfaEnforcedEvaluator(EvaluatorBase):
    evaluator_type = "mfa_enforced"
    description = "All active users must have MFA enrolled"

    def evaluate(self, data: dict, config: dict) -> CheckResult:
        users = data.get("users", [])
        if not users:
            return CheckResult(
                status=Status.ERROR,
                summary="No user data returned from connector",
                evaluator_type=self.evaluator_type,
            )

        # Filter to active users (configurable status field)
        active_status = config.get("active_status", "ACTIVE")
        active_users = [u for u in users if u.get("status") == active_status]

        # Optional: exclude service accounts or specific users
        exclude = set(config.get("exclude_users", []))
        active_users = [u for u in active_users if u.get("email") not in exclude]

        non_compliant = [u for u in active_users if not u.get("mfa_enrolled")]

        failures = [
            FailingResource(
                resource_type="user",
                resource_id=u.get("email", u.get("id", "unknown")),
                reason="MFA not enrolled",
                details={
                    "user_id": u.get("id"),
                    "status": u.get("status"),
                    "last_login": u.get("last_login"),
                    "mfa_factors": u.get("mfa_factors", []),
                },
            )
            for u in non_compliant
        ]

        total = len(active_users)
        compliant = total - len(non_compliant)
        rate = round(compliant / total, 4) if total > 0 else 0

        evidence = {
            "total_users": len(users),
            "active_users": total,
            "mfa_compliant": compliant,
            "mfa_non_compliant": len(non_compliant),
            "compliance_rate": rate,
            "non_compliant_users": [u.get("email") for u in non_compliant],
        }

        if non_compliant:
            return CheckResult(
                status=Status.FAIL,
                summary=f"{len(non_compliant)} of {total} active users do not have MFA enrolled",
                evidence=evidence,
                failures=failures,
                evaluator_type=self.evaluator_type,
            )

        return CheckResult(
            status=Status.PASS,
            summary=f"All {total} active users have MFA enrolled",
            evidence=evidence,
            evaluator_type=self.evaluator_type,
        )

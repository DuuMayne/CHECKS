"""Branch protection evaluator — checks that critical repos have protection enabled."""
from .base import EvaluatorBase, evaluator
from ..models import CheckResult, FailingResource, Status


@evaluator
class BranchProtectionEvaluator(EvaluatorBase):
    evaluator_type = "branch_protection"
    description = "All critical repositories must have branch protection on their default branch"

    def evaluate(self, data: dict, config: dict) -> CheckResult:
        repos = data.get("repos", [])
        if not repos:
            return CheckResult(
                status=Status.ERROR,
                summary="No repository data returned from connector",
                evaluator_type=self.evaluator_type,
            )

        # Configurable minimum requirements
        min_reviews = config.get("min_required_reviews", 1)
        require_status_checks = config.get("require_status_checks", False)

        unprotected = []
        insufficient = []

        for repo in repos:
            prot = repo.get("branch_protection")
            if prot is None or not prot.get("enabled"):
                unprotected.append(repo)
            elif prot.get("required_reviews", 0) < min_reviews:
                insufficient.append(repo)

        non_compliant = unprotected + insufficient

        failures = [
            FailingResource(
                resource_type="repository",
                resource_id=r["full_name"],
                reason="No branch protection" if r in unprotected else f"Requires {min_reviews} reviews, has {r.get('branch_protection', {}).get('required_reviews', 0)}",
                details={
                    "default_branch": r.get("default_branch"),
                    "branch_protection": r.get("branch_protection"),
                },
            )
            for r in non_compliant
        ]

        evidence = {
            "total_repos": len(repos),
            "protected": len(repos) - len(non_compliant),
            "unprotected": len(unprotected),
            "insufficient_reviews": len(insufficient),
            "non_compliant_repos": [r["full_name"] for r in non_compliant],
            "repo_details": [
                {
                    "full_name": r["full_name"],
                    "default_branch": r.get("default_branch"),
                    "has_protection": r.get("branch_protection") is not None and r.get("branch_protection", {}).get("enabled", False),
                    "required_reviews": r.get("branch_protection", {}).get("required_reviews", 0) if r.get("branch_protection") else 0,
                }
                for r in repos
            ],
        }

        if non_compliant:
            return CheckResult(
                status=Status.FAIL,
                summary=f"{len(non_compliant)} of {len(repos)} repos lack adequate branch protection",
                evidence=evidence,
                failures=failures,
                evaluator_type=self.evaluator_type,
            )

        return CheckResult(
            status=Status.PASS,
            summary=f"All {len(repos)} repos have branch protection with >= {min_reviews} required reviews",
            evidence=evidence,
            evaluator_type=self.evaluator_type,
        )

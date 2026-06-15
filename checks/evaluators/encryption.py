"""S3 encryption evaluator — checks that all buckets have encryption at rest enabled."""

from ..models import CheckResult, FailingResource, Status
from .base import EvaluatorBase, evaluator


@evaluator
class S3EncryptionEvaluator(EvaluatorBase):
    evaluator_type = "s3_encryption"
    description = "All S3 buckets must have encryption at rest enabled"

    def evaluate(self, data: dict, config: dict) -> CheckResult:
        buckets = data.get("buckets", [])
        if not buckets:
            return CheckResult(
                status=Status.ERROR,
                summary="No bucket data returned from connector",
                evaluator_type=self.evaluator_type,
            )

        # Optional: only check specific buckets
        only_buckets = config.get("only_buckets")
        if only_buckets:
            buckets = [b for b in buckets if b["name"] in only_buckets]

        # Optional: exclude certain buckets (logging, temp, etc.)
        exclude = set(config.get("exclude_buckets", []))
        buckets = [b for b in buckets if b["name"] not in exclude]

        unencrypted = [b for b in buckets if not b.get("encryption_enabled")]

        failures = [
            FailingResource(
                resource_type="s3_bucket",
                resource_id=b["name"],
                reason="Server-side encryption not enabled",
                details={
                    "region": b.get("region"),
                    "public_access_blocked": b.get("public_access_blocked"),
                    "versioning": b.get("versioning"),
                },
            )
            for b in unencrypted
        ]

        evidence = {
            "total_buckets": len(buckets),
            "encrypted": len(buckets) - len(unencrypted),
            "unencrypted": len(unencrypted),
            "unencrypted_buckets": [b["name"] for b in unencrypted],
            "bucket_details": [
                {
                    "name": b["name"],
                    "encryption_enabled": b.get("encryption_enabled", False),
                    "encryption_algorithm": b.get("encryption_algorithm"),
                    "public_access_blocked": b.get("public_access_blocked"),
                }
                for b in buckets
            ],
        }

        if unencrypted:
            return CheckResult(
                status=Status.FAIL,
                summary=f"{len(unencrypted)} of {len(buckets)} S3 buckets lack encryption at rest",
                evidence=evidence,
                failures=failures,
                evaluator_type=self.evaluator_type,
            )

        return CheckResult(
            status=Status.PASS,
            summary=f"All {len(buckets)} S3 buckets have encryption at rest enabled",
            evidence=evidence,
            evaluator_type=self.evaluator_type,
        )

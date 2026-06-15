"""AWS connector — fetches IAM, CloudTrail, and S3 security state."""
import os
from datetime import datetime, timezone

from .base import ConnectorBase, connector


@connector
class AWSConnector(ConnectorBase):
    connector_type = "aws"
    required_env = ["AWS_ACCESS_KEY_ID"]  # Or uses default credential chain
    mock_data = {
        "accounts": [
            {"account_id": "123456789012", "account_name": "prod", "cloudtrail_enabled": True, "is_logging": True, "trail_name": "org-trail"},
        ],
        "access_keys": [
            {"user_name": "deployer", "access_key_id": "AKIA1234", "status": "Active", "age_days": 45, "last_used": "2026-06-10"},
            {"user_name": "old-service", "access_key_id": "AKIA5678", "status": "Active", "age_days": 120, "last_used": "2026-03-01"},
        ],
        "buckets": [
            {"name": "prod-data", "encryption_enabled": True, "encryption_algorithm": "AES256", "public_access_blocked": True, "versioning": "Enabled"},
            {"name": "logs-archive", "encryption_enabled": True, "encryption_algorithm": "aws:kms", "public_access_blocked": True, "versioning": "Enabled"},
            {"name": "temp-uploads", "encryption_enabled": False, "public_access_blocked": True, "versioning": "Suspended"},
        ],
    }

    def __init__(self):
        import boto3
        region = os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "us-east-1"))
        profile = os.environ.get("AWS_PROFILE")
        self.session = boto3.Session(profile_name=profile, region_name=region)

    def test_connection(self) -> bool:
        try:
            self.session.client("sts").get_caller_identity()
            return True
        except Exception:
            return False

    def fetch(self, config: dict) -> dict:
        """Fetch AWS security data. Config determines what to collect:

        - fetch_cloudtrail: bool (check trail status)
        - fetch_access_keys: bool (check key ages)
        - fetch_s3: bool (check bucket encryption)
        - production_accounts: list (for CloudTrail multi-account)
        """
        result = {}

        if config.get("fetch_cloudtrail", True):
            result["accounts"] = self._fetch_cloudtrail(config)

        if config.get("fetch_access_keys", True):
            result["access_keys"] = self._fetch_access_keys()

        if config.get("fetch_s3", True):
            result["buckets"] = self._fetch_s3_encryption()

        return result

    def _fetch_cloudtrail(self, config: dict) -> list[dict]:
        ct = self.session.client("cloudtrail")
        try:
            trails = ct.describe_trails(includeShadowTrails=False).get("trailList", [])
            if not trails:
                identity = self.session.client("sts").get_caller_identity()
                return [{
                    "account_id": identity["Account"],
                    "account_name": identity.get("Arn", "").split("/")[-1],
                    "cloudtrail_enabled": False,
                    "is_logging": False,
                    "trail_name": None,
                }]

            accounts = []
            for trail in trails:
                status = ct.get_trail_status(Name=trail["TrailARN"])
                accounts.append({
                    "account_id": trail.get("HomeRegion", ""),
                    "account_name": trail.get("Name", ""),
                    "cloudtrail_enabled": True,
                    "is_logging": status.get("IsLogging", False),
                    "trail_name": trail["Name"],
                })
            return accounts
        except Exception as e:
            return [{"account_id": "unknown", "cloudtrail_enabled": False, "is_logging": False, "error": str(e)}]

    def _fetch_access_keys(self) -> list[dict]:
        iam = self.session.client("iam")
        keys = []
        now = datetime.now(timezone.utc)

        paginator = iam.get_paginator("list_users")
        for page in paginator.paginate():
            for user in page["Users"]:
                user_keys = iam.list_access_keys(UserName=user["UserName"])["AccessKeyMetadata"]
                for k in user_keys:
                    age = (now - k["CreateDate"].replace(tzinfo=timezone.utc)).days
                    last_used_resp = iam.get_access_key_last_used(AccessKeyId=k["AccessKeyId"])
                    last_used = last_used_resp.get("AccessKeyLastUsed", {}).get("LastUsedDate")

                    keys.append({
                        "user_name": user["UserName"],
                        "access_key_id": k["AccessKeyId"],
                        "status": k["Status"],
                        "age_days": age,
                        "last_used": last_used.isoformat() if last_used else None,
                    })
        return keys

    def _fetch_s3_encryption(self) -> list[dict]:
        s3 = self.session.client("s3")
        buckets = []

        for bucket in s3.list_buckets().get("Buckets", []):
            name = bucket["Name"]
            entry = {"name": name, "encryption_enabled": False}

            try:
                enc = s3.get_bucket_encryption(Bucket=name)
                rules = enc.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
                if rules:
                    entry["encryption_enabled"] = True
                    entry["encryption_algorithm"] = rules[0].get("ApplyServerSideEncryptionByDefault", {}).get("SSEAlgorithm")
            except Exception:
                entry["encryption_enabled"] = False

            try:
                pub = s3.get_public_access_block(Bucket=name)
                cfg = pub.get("PublicAccessBlockConfiguration", {})
                entry["public_access_blocked"] = all(cfg.values()) if cfg else False
            except Exception:
                entry["public_access_blocked"] = False

            try:
                ver = s3.get_bucket_versioning(Bucket=name)
                entry["versioning"] = ver.get("Status", "Disabled")
            except Exception:
                entry["versioning"] = "Unknown"

            buckets.append(entry)

        return buckets

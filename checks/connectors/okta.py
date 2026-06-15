from __future__ import annotations

"""Okta connector — fetches user and MFA enrollment data."""
import os

import httpx

from .base import ConnectorBase, connector


@connector
class OktaConnector(ConnectorBase):
    connector_type = "okta"
    required_env = ["OKTA_DOMAIN", "OKTA_API_TOKEN"]
    mock_data = {
        "users": [
            {
                "id": "u1",
                "email": "alice@company.com",
                "status": "ACTIVE",
                "mfa_enrolled": True,
                "mfa_factors": ["okta_verify"],
                "last_login": "2026-06-10T10:00:00Z",
            },
            {
                "id": "u2",
                "email": "bob@company.com",
                "status": "ACTIVE",
                "mfa_enrolled": True,
                "mfa_factors": ["okta_verify", "sms"],
                "last_login": "2026-06-12T09:00:00Z",
            },
            {
                "id": "u3",
                "email": "charlie@company.com",
                "status": "ACTIVE",
                "mfa_enrolled": False,
                "mfa_factors": [],
                "last_login": "2026-05-01T09:00:00Z",
            },
            {
                "id": "u4",
                "email": "service-account@company.com",
                "status": "ACTIVE",
                "mfa_enrolled": False,
                "mfa_factors": [],
                "last_login": None,
            },
            {
                "id": "u5",
                "email": "former@company.com",
                "status": "DEPROVISIONED",
                "mfa_enrolled": False,
                "mfa_factors": [],
                "last_login": "2026-01-15T08:00:00Z",
            },
        ]
    }

    def __init__(self):
        self.domain = os.environ["OKTA_DOMAIN"]
        self.base_url = f"https://{self.domain}"
        self.headers = {
            "Authorization": f"SSWS {os.environ['OKTA_API_TOKEN']}",
            "Accept": "application/json",
        }

    def test_connection(self) -> bool:
        try:
            resp = httpx.get(f"{self.base_url}/api/v1/users?limit=1", headers=self.headers, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def fetch(self, config: dict) -> dict:
        users = self._fetch_all_users()
        for user in users:
            if user["status"] == "ACTIVE":
                factors = self._fetch_factors(user["id"])
                user["mfa_enrolled"] = len(factors) > 0
                user["mfa_factors"] = [f["factorType"] for f in factors]
            else:
                user["mfa_enrolled"] = False
                user["mfa_factors"] = []
        return {"users": users}

    def _fetch_all_users(self) -> list[dict]:
        users = []
        url = f"{self.base_url}/api/v1/users?limit=200"
        while url:
            resp = httpx.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            for u in resp.json():
                users.append(
                    {
                        "id": u["id"],
                        "email": u.get("profile", {}).get("email", ""),
                        "status": u.get("status", "UNKNOWN"),
                        "last_login": u.get("lastLogin"),
                    }
                )
            url = self._next_link(resp.headers.get("link"))
        return users

    def _fetch_factors(self, user_id: str) -> list[dict]:
        try:
            resp = httpx.get(
                f"{self.base_url}/api/v1/users/{user_id}/factors",
                headers=self.headers,
                timeout=10,
            )
            resp.raise_for_status()
            return [f for f in resp.json() if f.get("status") == "ACTIVE"]
        except Exception:
            return []

    @staticmethod
    def _next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None
        for part in link_header.split(","):
            if 'rel="next"' in part:
                return part.split(";")[0].strip().strip("<>")
        return None

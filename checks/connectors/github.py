from __future__ import annotations
"""GitHub connector — fetches branch protection and security settings."""
import os

import httpx

from .base import ConnectorBase, connector


@connector
class GitHubConnector(ConnectorBase):
    connector_type = "github"
    required_env = ["GITHUB_TOKEN"]
    mock_data = {
        "repos": [
            {
                "full_name": "acme/api-service",
                "default_branch": "main",
                "branch_protection": {"enabled": True, "required_reviews": 2, "enforce_admins": True, "dismiss_stale_reviews": True, "required_status_checks": True},
            },
            {
                "full_name": "acme/frontend",
                "default_branch": "main",
                "branch_protection": {"enabled": True, "required_reviews": 1, "enforce_admins": False, "dismiss_stale_reviews": True, "required_status_checks": True},
            },
            {
                "full_name": "acme/infra-config",
                "default_branch": "main",
                "branch_protection": None,
            },
        ]
    }

    BASE_URL = "https://api.github.com"

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def test_connection(self) -> bool:
        try:
            resp = httpx.get(f"{self.BASE_URL}/user", headers=self.headers, timeout=10)
            return resp.status_code == 200
        except Exception:
            return False

    def fetch(self, config: dict) -> dict:
        repos_to_check = config.get("critical_repos", [])
        if not repos_to_check:
            # Fall back to fetching all org repos
            org = config.get("org") or os.environ.get("GITHUB_ORG", "")
            if org:
                repos_to_check = self._list_org_repos(org)

        repos = []
        for repo_name in repos_to_check:
            repos.append(self._fetch_repo_protection(repo_name))
        return {"repos": repos}

    def _list_org_repos(self, org: str) -> list[str]:
        repos = []
        url = f"{self.BASE_URL}/orgs/{org}/repos?per_page=100&type=all"
        while url:
            resp = httpx.get(url, headers=self.headers, timeout=30)
            resp.raise_for_status()
            repos.extend(r["full_name"] for r in resp.json() if not r.get("archived"))
            url = self._next_link(resp.headers.get("link"))
        return repos

    def _fetch_repo_protection(self, repo_full_name: str) -> dict:
        try:
            repo_resp = httpx.get(f"{self.BASE_URL}/repos/{repo_full_name}", headers=self.headers, timeout=10)
            repo_resp.raise_for_status()
            default_branch = repo_resp.json().get("default_branch", "main")
        except Exception as e:
            return {"full_name": repo_full_name, "default_branch": "unknown", "branch_protection": None, "error": str(e)}

        try:
            prot_resp = httpx.get(
                f"{self.BASE_URL}/repos/{repo_full_name}/branches/{default_branch}/protection",
                headers=self.headers, timeout=10,
            )
            if prot_resp.status_code == 404:
                return {"full_name": repo_full_name, "default_branch": default_branch, "branch_protection": None}

            prot_resp.raise_for_status()
            prot = prot_resp.json()
            reviews = prot.get("required_pull_request_reviews")

            return {
                "full_name": repo_full_name,
                "default_branch": default_branch,
                "branch_protection": {
                    "enabled": True,
                    "required_reviews": reviews.get("required_approving_review_count", 0) if reviews else 0,
                    "dismiss_stale_reviews": reviews.get("dismiss_stale_reviews", False) if reviews else False,
                    "enforce_admins": prot.get("enforce_admins", {}).get("enabled", False),
                    "required_status_checks": prot.get("required_status_checks") is not None,
                },
            }
        except Exception as e:
            return {"full_name": repo_full_name, "default_branch": default_branch, "branch_protection": None, "error": str(e)}

    @staticmethod
    def _next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None
        for part in link_header.split(","):
            if 'rel="next"' in part:
                return part.split(";")[0].strip().strip("<>")
        return None

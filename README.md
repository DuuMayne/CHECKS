# CHECKS — Compliance Check Library

A simple, portable toolkit that answers one question: **"Are my security controls actually working right now?"**

You tell it what systems you use (Okta, AWS, GitHub, etc.), what you care about (MFA enabled? Buckets encrypted? Keys rotated?), and it gives you a clear **pass or fail** — plus the evidence to prove it.

---

## The Big Picture

Think of it like automated health checks for your security program:

```
You define:   "Check that all our users have MFA turned on"
                           ↓
CHECKS does:   Logs into Okta → pulls user list → counts who has MFA
                           ↓
You get back:  ✗ FAIL — 3 of 47 active users don't have MFA
               └─ charlie@company.com: MFA not enrolled
               └─ new-hire@company.com: MFA not enrolled
               └─ contractor@company.com: MFA not enrolled
```

No guessing. No screenshots. No "I think we're compliant." Just a definitive answer with receipts.

---

## Part of the PANOPTICON Suite

CHECKS is one piece of a three-part system for GRC engineers:

| Tool | What it does | Repo |
|------|-------------|------|
| **CHECKS** (this) | Shared check library — deterministic pass/fail logic + connectors | The primitive |
| **[OCULUS](https://github.com/DuuMayne/OCULUS)** | Runs checks continuously, stores results, alerts on drift | The monitor |
| **[EXHIBIT](https://github.com/DuuMayne/EXHIBIT)** | Packages evidence for auditors — maps frameworks, generates explainers | The audit response |

**You don't need all three.** CHECKS works standalone — just run `checks run` from your laptop whenever you want to know "how are we doing?" Add OCULUS when you want continuous monitoring. Add EXHIBIT when an auditor shows up.

The system forms a feedback loop: OCULUS monitors → EXHIBIT surfaces gaps → you build new checks → coverage improves → audit costs go down.

---

## Getting Started

### What You Need

- Python 3.9 or newer (check with `python3 --version` in Terminal)
- API credentials for at least one system you want to check (Okta, AWS, or GitHub)

### Step 1: Get the Code

Open Terminal (on Mac: search "Terminal" in Spotlight) and run:

```bash
git clone https://github.com/DuuMayne/CHECKS.git
cd CHECKS
```

### Step 2: Install It

```bash
pip3 install -e .
```

This installs the `checks` command on your machine. The `-e` means "editable" — if you change the config, it picks it up immediately.

### Step 3: Create Your Configuration

```bash
checks init
```

This creates a file called `checks.yml` in your current folder. Open it in any text editor — it looks like this:

```yaml
checks:
  mfa_enforced:
    connector: okta
    evaluator: mfa_enforced
    config:
      exclude_users:
        - service-bot@company.com
```

**That's a complete check definition.** It says:
- **connector: okta** — "get data from Okta"
- **evaluator: mfa_enforced** — "check if everyone has MFA"
- **config** — "but ignore service-bot, that's expected"

### Step 4: Add Your Credentials

CHECKS needs API access to your systems. Set these as environment variables:

**For Okta:**
```bash
export OKTA_DOMAIN="yourcompany.okta.com"
export OKTA_API_TOKEN="your-token-here"
```

**For GitHub:**
```bash
export GITHUB_TOKEN="ghp_your-token-here"
export GITHUB_ORG="your-org-name"
```

**For AWS:**
```bash
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_REGION="us-east-1"
```

(You only need the ones for systems you're actually checking.)

### Step 5: Run Your Checks

```bash
checks run
```

That's it. You'll see output like:

```
============================================================
  Running 5 check(s)
============================================================

  [mfa_enforced] ✗ FAIL — 3 of 47 active users do not have MFA enrolled
         └─ charlie@company.com: MFA not enrolled
         └─ new-hire@company.com: MFA not enrolled
         └─ contractor@company.com: MFA not enrolled
  [branch_protection] ✓ PASS — All 12 repos have branch protection with >= 1 required reviews
  [s3_encryption] ✓ PASS — All 8 S3 buckets have encryption at rest enabled
  [key_rotation] ✗ FAIL — 2 active access keys exceed 90-day rotation threshold
         └─ deployer/AKIA1234: Key is 127 days old (max: 90)
         └─ ci-bot/AKIA5678: Key is 203 days old (max: 90)
  [cloudtrail_logging] ✓ PASS — All 1 accounts have CloudTrail actively logging

============================================================
  Results: 3 passed, 2 failed, 0 errors
============================================================
```

### Step 6: Run a Single Check

Don't want to run everything? Just name the one you care about:

```bash
checks run mfa_enforced
```

---

## Customizing for Your Environment

### "We use Azure AD, not Okta"

Change one line in your `checks.yml`:

```yaml
mfa_enforced:
  connector: azure_ad    # ← was "okta"
  evaluator: mfa_enforced
```

(Once the Azure AD connector is built — the architecture supports any identity provider.)

### "We only care about certain repos"

```yaml
branch_protection:
  connector: github
  evaluator: branch_protection
  config:
    critical_repos:
      - company/api-service
      - company/payment-processor
      - company/infrastructure
    min_required_reviews: 2
```

### "Our key rotation policy is 60 days, not 90"

```yaml
key_rotation:
  connector: aws
  evaluator: access_key_rotation
  config:
    max_key_age_days: 60
```

### "I want to exclude some buckets from the encryption check"

```yaml
s3_encryption:
  connector: aws
  evaluator: s3_encryption
  config:
    exclude_buckets:
      - temp-scratch-data
      - public-static-assets
```

---

## Useful Commands

| Command | What it does |
|---------|-------------|
| `checks run` | Run all your checks |
| `checks run mfa_enforced` | Run one specific check |
| `checks list` | Show available connectors and evaluators |
| `checks status` | Show which systems have credentials configured |
| `checks validate` | Make sure your checks.yml doesn't have typos |
| `checks init` | Create a starter checks.yml |

---

## How It Works Under the Hood

Every check has two parts:

1. **Connector** — talks to the external system's API, handles authentication, pagination, and rate limiting. Returns raw data in a standard format.

2. **Evaluator** — receives that data and applies logic. "Are all users MFA-enrolled? Count the ones that aren't. Return pass or fail."

The connector handles the messy API stuff. The evaluator is just clean logic. This means:

- You can test evaluators without real credentials (mock data is built in)
- You can swap connectors without changing the check logic
- Adding a new system is writing one connector file

---

## Available Checks (Built-in)

| Check | What it verifies | Connector |
|-------|-----------------|-----------|
| `mfa_enforced` | All active users have MFA enrolled | Okta |
| `branch_protection` | Critical repos have branch protection enabled | GitHub |
| `s3_encryption` | All S3 buckets have encryption at rest | AWS |
| `access_key_rotation` | No access keys older than threshold | AWS |
| `cloudtrail_enabled` | Audit logging is active in all accounts | AWS |

More coming. And you can write your own — see the developer section below.

---

## Try Without Any Credentials (Demo Mode)

Every connector ships with realistic mock data. If you don't have credentials configured, CHECKS automatically uses the mock data so you can see how everything works:

```bash
checks init
checks run
```

You'll see failures in the mock data (intentionally — so you can see what a real failure looks like). When you add real credentials, it seamlessly switches to your actual systems.

---

## For Developers: Adding a New Check

### Adding a new evaluator (new pass/fail logic)

Create `checks/evaluators/my_check.py`:

```python
from .base import EvaluatorBase, evaluator
from ..models import CheckResult, FailingResource, Status

@evaluator
class MyCheckEvaluator(EvaluatorBase):
    evaluator_type = "my_check"
    description = "Verify something important"

    def evaluate(self, data: dict, config: dict) -> CheckResult:
        items = data.get("items", [])
        bad = [i for i in items if not i.get("compliant")]

        if bad:
            return CheckResult(
                status=Status.FAIL,
                summary=f"{len(bad)} items are non-compliant",
                failures=[
                    FailingResource(
                        resource_type="item",
                        resource_id=i["id"],
                        reason="Not compliant",
                    )
                    for i in bad
                ],
            )

        return CheckResult(status=Status.PASS, summary="All good")
```

Then import it in `checks/evaluators/__init__.py` and it's immediately available.

### Adding a new connector (new data source)

Create `checks/connectors/my_system.py`:

```python
from .base import ConnectorBase, connector

@connector
class MySystemConnector(ConnectorBase):
    connector_type = "my_system"
    required_env = ["MY_SYSTEM_API_KEY"]
    mock_data = {"items": [{"id": "test", "compliant": True}]}

    def fetch(self, config: dict) -> dict:
        # Your API logic here
        ...

    def test_connection(self) -> bool:
        # Verify credentials
        ...
```

Import it in `checks/connectors/__init__.py` and it's registered.

---

## License

| What | License |
|---|---|
| Source code | [Elastic License 2.0](LICENSE) |
| Documentation & templates | [CC BY-NC 4.0](LICENSE-docs) |

Free for anyone to use, fork, and build on — including commercially within your own organization. The one restriction: you cannot offer this software as a paid hosted or managed service. See [LICENSE](LICENSE) for full terms.

Copyright 2026 Adam Duman
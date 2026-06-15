"""
CLI for the checks library.

Usage:
    checks run                  — Run all checks defined in checks.yml
    checks run <key>            — Run a specific check by key
    checks list                 — List available connectors and evaluators
    checks status               — Show which connectors have credentials configured
    checks validate             — Validate your checks.yml config
    checks init                 — Create a starter checks.yml in the current directory
"""

import sys

from .config import find_config_path, load_config, validate_config
from .connectors import list_connectors
from .evaluators import list_evaluators
from .models import Status
from .runner import run_check_from_definition


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    cmd = args[0]

    if cmd == "run":
        _cmd_run(args[1:])
    elif cmd == "list":
        _cmd_list()
    elif cmd == "status":
        _cmd_status()
    elif cmd == "validate":
        _cmd_validate()
    elif cmd == "init":
        _cmd_init()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


def _cmd_run(args: list[str]):
    config = load_config()
    checks = config.get("checks", {})

    if not checks:
        print("No checks defined. Run 'checks init' to create a checks.yml.")
        sys.exit(1)

    # Run specific check or all
    if args:
        key = args[0]
        if key not in checks:
            print(f"Unknown check: '{key}'. Available: {list(checks.keys())}")
            sys.exit(1)
        keys_to_run = [key]
    else:
        keys_to_run = list(checks.keys())

    print(f"\n{'=' * 60}")
    print(f"  Running {len(keys_to_run)} check(s)")
    print(f"{'=' * 60}\n")

    results = []
    for key in keys_to_run:
        defn = {"key": key, **checks[key]}
        print(f"  [{key}] ", end="", flush=True)
        result = run_check_from_definition(defn)
        results.append(result)

        icon = "✓" if result.passed else ("✗" if result.status == Status.FAIL else "!")
        print(f"{icon} {result.status.value.upper()} — {result.summary} ({result.duration_ms}ms)")

        if result.failures:
            for f in result.failures[:5]:
                print(f"         └─ {f.resource_id}: {f.reason}")
            if len(result.failures) > 5:
                print(f"         └─ ... and {len(result.failures) - 5} more")

    # Summary
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if r.status == Status.FAIL)
    errors = sum(1 for r in results if r.status == Status.ERROR)

    print(f"\n{'=' * 60}")
    print(f"  Results: {passed} passed, {failed} failed, {errors} errors")
    print(f"{'=' * 60}\n")

    sys.exit(0 if failed == 0 and errors == 0 else 1)


def _cmd_list():
    print("\n=== Evaluators (pass/fail checks) ===\n")
    for name, desc in list_evaluators().items():
        print(f"  {name:<30} {desc}")

    print("\n=== Connectors (data sources) ===\n")
    for name, info in list_connectors().items():
        status = "configured" if info["configured"] else "not configured"
        print(f"  {name:<30} [{status}]")

    print()


def _cmd_status():
    print("\n=== Connector Status ===\n")
    for name, info in list_connectors().items():
        if info["configured"]:
            print(f"  ✓ {name:<25} ready")
        else:
            missing = ", ".join(info["required_env"])
            print(f"  ✗ {name:<25} needs: {missing}")
    print()


def _cmd_validate():
    path = find_config_path()
    if not path:
        print("No checks.yml found. Run 'checks init' to create one.")
        sys.exit(1)

    print(f"Validating: {path}")
    config = load_config(path)
    errors = validate_config(config)

    if errors:
        print(f"\n{len(errors)} error(s) found:\n")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        checks_count = len(config.get("checks", {}))
        print(f"  ✓ Valid — {checks_count} check(s) defined")


def _cmd_init():
    import shutil
    from pathlib import Path

    target = Path("checks.yml")
    if target.exists():
        print("checks.yml already exists. Delete it first or edit it directly.")
        sys.exit(1)

    example = Path(__file__).parent.parent / "checks.example.yml"
    if example.exists():
        shutil.copy(example, target)
    else:
        # Inline minimal template
        target.write_text("""# CHECKS configuration — edit this for your environment
checks:
  mfa_enforced:
    connector: okta
    evaluator: mfa_enforced
    config: {}

  branch_protection:
    connector: github
    evaluator: branch_protection
    config:
      critical_repos: []
""")

    print("Created checks.yml — edit it with your environment's details.")
    print("Then run: checks validate && checks run")


if __name__ == "__main__":
    main()

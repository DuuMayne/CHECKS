.PHONY: install lint format security test check ci clean

# Install dev dependencies
install:
	pip install -e ".[dev]"
	pre-commit install

# Lint (check only, no changes)
lint:
	ruff check checks/ tests/
	ruff format --check checks/ tests/

# Format (auto-fix)
format:
	ruff check --fix checks/ tests/
	ruff format checks/ tests/

# Security scan
security:
	bandit -r checks/ -c pyproject.toml
	pip-audit

# Run tests
test:
	pytest tests/ -v --cov=checks --cov-report=term-missing

# Run everything (what CI does)
check: lint security test
	@echo "\n✓ All checks passed"

# Quick check (what pre-commit does)
ci: lint test
	@echo "\n✓ CI checks passed"

# Clean up
clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

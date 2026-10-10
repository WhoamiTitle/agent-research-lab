.PHONY: lint test check

lint:
	uv run --locked ruff check --no-fix src tests infra/hermes/provision.py
	uv run --locked ruff format --check src tests infra/hermes/provision.py
	uv run --locked mypy
	PYTHONPATH=src uv run --locked lint-imports

test:
	uv run --locked pytest

check: lint test
	bash -n scripts/lab.sh

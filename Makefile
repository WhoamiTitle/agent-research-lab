# Shell config
SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c

# Make config
.DEFAULT_GOAL := check
.SILENT:
MAKEFLAGS += --no-print-directory

# Script aliases
PIP_AUDIT := scripts/makefile/pip_audit.sh
PYCACHE_DEL := scripts/makefile/pycache_del.sh
SELF_RETURN := scripts/makefile/self_return.py
SHELLCHECK := scripts/makefile/shellcheck.sh
SLOTSCHECK := scripts/makefile/slotscheck.sh

# Quality
.PHONY: lint format shellcheck slotscheck test check check-ci pip-audit

lint:
	uv run --locked ruff check --no-fix src tests scripts infra
	uv run --locked ruff format --check src tests scripts infra
	uv run --locked tombi format --check pyproject.toml
	uv run --locked tombi lint pyproject.toml
	uv run --locked deptry
	$(MAKE) shellcheck slotscheck
	PYTHONPATH=src uv run --locked lint-imports
	uv run --locked python3 $(SELF_RETURN) src tests scripts infra
	uv run --locked mypy

format:
	uv run --locked ruff check --fix --no-unsafe-fixes src tests scripts infra
	uv run --locked ruff format src tests scripts infra
	uv run --locked tombi format pyproject.toml

shellcheck:
	$(SHELLCHECK)

slotscheck:
	$(SLOTSCHECK) src infra scripts

test:
	uv run --locked pytest --cov --cov-report=term-missing --cov-report=html

check: lint test

check-ci: check

pip-audit:
	$(PIP_AUDIT)

# Utils
.PHONY: pycache-del hooks
pycache-del:
	$(PYCACHE_DEL)

hooks:
	uv run --locked prek install --config .pre-commit-config.yaml

#!/bin/bash
# The script is called from Makefile.
set -eu -o pipefail

audit_requirements=$(mktemp)
trap 'unlink "$audit_requirements"' EXIT

uv export --locked --no-emit-project --format requirements-txt \
  --no-header --output-file "$audit_requirements" >/dev/null
uv run --locked pip-audit --requirement "$audit_requirements" --require-hashes --disable-pip

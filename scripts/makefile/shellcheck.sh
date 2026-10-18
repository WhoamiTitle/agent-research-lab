#!/bin/bash
# The script is called from Makefile.
set -eu -o pipefail

scripts=(
  scripts/lab.sh
  scripts/makefile/*.sh
  scripts/evidence/*.command
  infra/hermes/expire-gateway-logs.sh
)
for script in "${scripts[@]}"; do
  bash -n "$script"
done
uv run --locked shellcheck --severity=warning "${scripts[@]}"

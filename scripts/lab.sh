#!/usr/bin/env bash
set -eu -o pipefail

task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec env PYTHONPATH="$task_root/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m agent_lab "$@"

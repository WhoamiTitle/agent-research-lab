#!/usr/bin/env bash
set -euo pipefail

task_log_dir=/srv/agent-lab/data/logs/gateways
if [[ -d "$task_log_dir" && ! -L "$task_log_dir" ]]; then
  # s6 names completed archives @<timestamp>.s. Keep current and lock files.
  find "$task_log_dir" -type f -name '@*.s' -mtime +14 -delete
fi

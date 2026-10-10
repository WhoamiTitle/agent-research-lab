#!/usr/bin/env bash
set -euo pipefail

task_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
task_compose=/srv/agent-lab/deployment/infra/hermes/compose.yaml

case "${1:-help}" in
  start|stop|status)
    PYTHONPATH="$task_root/src${PYTHONPATH:+:$PYTHONPATH}" python3 -m agent_lab "$1"
    ;;
  model)
    ollama pull qwen3.5:4b
    ollama create agent-lab-qwen:4b -f "$task_root/infra/ollama/Modelfile"
    ;;
  sync)
    # Transfer only reviewed deployment files, never host state or credentials.
    COPYFILE_DISABLE=1 tar --no-xattrs --exclude=__pycache__ --exclude='*.pyc' -C "$task_root" -cf - infra/hermes templates |
      limactl shell agent-research -- sudo tar -xf - -C /srv/agent-lab/deployment
    limactl shell agent-research -- sudo bash -s <<'GUEST'
set -euo pipefail
task_deploy=/srv/agent-lab/deployment
task_data=/srv/agent-lab/data
if [[ ! -f "$task_data/config.yaml" ]]; then
  install -m 0600 -o researcher -g researcher "$task_deploy/infra/hermes/config.yaml" "$task_data/config.yaml"
fi
if [[ ! -f "$task_data/.env" ]]; then
  install -m 0600 -o researcher -g researcher "$task_deploy/templates/hermes.env.example" "$task_data/.env"
fi
install -d -m 0700 -o researcher -g researcher "$task_data/memories" "$task_data/workspace" "$task_data/logs" "$task_data/logs/gateways"
for task_memory in USER.md MEMORY.md; do
  if [[ ! -f "$task_data/memories/$task_memory" ]]; then
    install -m 0600 -o researcher -g researcher "$task_deploy/templates/memory/$task_memory" "$task_data/memories/$task_memory"
  fi
done
install -d -m 0700 -o researcher -g researcher "$task_data/skills" "$task_data/skills/lab-readiness"
install -m 0600 -o researcher -g researcher "$task_deploy/templates/skills/lab-readiness/SKILL.md" "$task_data/skills/lab-readiness/SKILL.md"
install -m 0644 "$task_deploy/infra/hermes/logrotate.conf" /etc/logrotate.d/agent-research-lab
install -m 0755 "$task_deploy/infra/hermes/expire-gateway-logs.sh" /usr/local/sbin/agent-lab-expire-gateway-logs
install -m 0644 "$task_deploy/infra/hermes/log-retention.service" /etc/systemd/system/agent-lab-log-retention.service
install -m 0644 "$task_deploy/infra/hermes/log-retention.timer" /etc/systemd/system/agent-lab-log-retention.timer
systemctl daemon-reload
systemctl enable --now agent-lab-log-retention.timer
GUEST
    ;;
  setup)
    limactl shell agent-research -- sudo docker compose -f "$task_compose" run --rm hermes setup
    ;;
  web-deps)
    limactl shell agent-research -- sudo docker compose -f "$task_compose" run --rm hermes pm install --extra ddgs
    limactl shell agent-research -- sudo docker compose -f "$task_compose" run --rm hermes pm install agent-browser
    ;;
  chat)
    shift
    limactl shell agent-research -- sudo docker compose -f "$task_compose" run --rm hermes chat "$@"
    ;;
  gateway)
    limactl shell agent-research -- sudo docker compose -f "$task_compose" run --rm \
      -v /srv/agent-lab/deployment/infra/hermes/preflight.py:/opt/preflight.py:ro \
      hermes python /opt/preflight.py
    limactl shell agent-research -- curl -fsS --max-time 5 http://127.0.0.1:11434/api/version
    limactl shell agent-research -- sudo docker compose -f "$task_compose" up -d
    ;;
  *)
    echo 'Usage: scripts/lab.sh start|stop|model|sync|setup|web-deps|chat|gateway|status'
    ;;
esac

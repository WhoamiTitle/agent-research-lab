#!/usr/bin/env bash
set -eu -o pipefail

p1_evidence_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd -- "$p1_evidence_root"

printf '%s\n' 'P1: ПРОСМОТР СОХРАНЁННЫХ ЖУРНАЛОВ. НОВЫЙ ЗАПУСК НЕ ВЫПОЛНЯЕТСЯ.'
jq -r '"Проверка: \(.checked_at_local) / America/Los_Angeles"' evidence/p1/autonomous-cron.json

printf '\n%s\n' 'Файл: evidence/p1/autonomous-cron-history.txt (исходные метки UTC)'
cat evidence/p1/autonomous-cron-history.txt

printf '\n%s\n' 'Источник: evidence/p1/autonomous-cron.json'
jq -r '
  "Задание: \(.execution.job_id); модель: \(.model_session.model)",
  "Назначено: \(.schedule.scheduled_for_local)",
  "Старт: \(.execution_started_at_local)",
  "Завершение: \(.execution_finished_at_local)",
  "status=\(.execution.status); source=\(.execution.source); error=\(.execution.error | tojson)",
  "deliver=\(.schedule.job_definition.deliver); delivery_outcome=\(.execution.delivery_outcome)",
  "Закрытие Telegram подтверждено владельцем: \(.telegram_client.closed_confirmed_by_user)",
  "Ручной cron run/tick: \(.verification.manual_tick_or_run_used); временный ticker: \(.verification.temporary_ticker_used)",
  "Контрольные расписания удалены: \(.verification.control_schedules_removed)"' evidence/p1/autonomous-cron.json

printf '\n%s\n' 'Файл: evidence/p1/autonomous-cron-result.txt'
cat evidence/p1/autonomous-cron-result.txt

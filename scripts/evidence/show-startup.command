#!/usr/bin/env bash
set -eu -o pipefail

p1_evidence_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd -- "$p1_evidence_root"

printf '%s\n' 'P1: ПРОСМОТР СОХРАНЁННЫХ ЖУРНАЛОВ. НОВЫЙ ЗАПУСК НЕ ВЫПОЛНЯЕТСЯ.'
jq -r '"Проверка: \(.checked_at_local) / America/Los_Angeles"' evidence/p1/skill-loading.json

printf '\n%s\n' 'Файл: evidence/p1/skill-loading-startup.log (исходные метки UTC)'
cat evidence/p1/skill-loading-startup.log

printf '\n%s\n' 'Источник: evidence/p1/skill-loading.json / controlled_run'
jq -r '.controlled_run |
  "Начало: \(.created_at_local)",
  "Завершение: \(.completed_at_local)",
  "Статус: \(.status); модель: \(.runtime.model)",
  (.tool_trace[] |
    if .event == "tool_call" then
      "CALL \(.tool) \(.arguments | tojson)"
    else
      "RESULT \(.tool) \(.result | tojson)"
    end
  )' evidence/p1/skill-loading.json

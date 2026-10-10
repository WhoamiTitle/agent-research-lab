# Исходные материалы

## Задание пользователя

- Файл: [assignment-02.txt](assignment-02.txt).
- Получен как текстовое вложение пользователя в этой беседе.
- Сохранён 10 октября 2026 года без изменения содержимого.
- SHA-256:

```text
8c7731a933fcc3ece33f1033864798e4334eab973eed1c844adda394c5e5f1d9
```

Проверка сохранённой копии из корня проекта:

```bash
shasum -a 256 sources/assignment-02.txt
```

Исходное задание сохраняет формулировки автора. Обсуждение их точности и
уточнения требований ведутся отдельно от этого файла.

## Уточнённый подготовительный этап

- Файл: [assignment-02-preparation.txt](assignment-02-preparation.txt).
- Получен отдельным вложением 10 октября 2026 года; содержит требования
  безопасности и раздел «Ход работы».
- Используется как текущая граница подготовки по указанию пользователя.
- Сохранён без редактирования; предыдущий полный текст также сохранён.
- SHA-256: `076d30c39f8e5cfd32f42179e275bbe6345a8dd98557c5fbfec732c740835e48`.

## Документация для настройки

Проверена 10 октября 2026 года:

- [Lima: установка](https://lima-vm.io/docs/installation/).
- [Docker Engine для Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
- [Hermes в Docker](https://hermes-agent.nousresearch.com/docs/user-guide/docker/).
- [Hermes: Telegram](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram/).
- [Ollama: настройка контекста](https://docs.ollama.com/context-length).
- [Qwen3.5 4B в Ollama](https://ollama.com/library/qwen3.5:4b).
- [Выбор браузерного движка в Hermes v0.21.6](https://github.com/NousResearch/hermes-agent/blob/v0.21.6/tools/browser_use_cli.py).
- [Флаг OLLAMA_NO_CLOUD в Ollama v0.35.1](https://github.com/ollama/ollama/blob/v0.35.1/envconfig/config.go).

Для Hermes выбран опубликованный Docker-тег `v0.21.6`; Compose дополнительно
закрепляет digest. Фактические результаты проверок находятся в
`evidence/preparation/`, а ограничения — в документе подготовки.

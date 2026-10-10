# Стиль кода и команды разработки

Референс — [fastapi-clean-example](https://github.com/ivan-borovets/fastapi-clean-example),
локальный снимок `5d68d52`. Из него взяты оформление Makefile, размещение
shell-помощников, профиль форматирования Python, абстрактные порты и набор
инструментов разработки. Прикладные области `stand`, `model`, `deployment`
и `hermes` сохраняют существующее оформление обработчиков `*Handler.__call__`.

## Python

- Длина строки — 120, двойные кавычки, абсолютные импорты и сортировка Ruff.
- Константы имеют `Final`, статусы и команды используют `StrEnum`.
- Контракты оформляются именованными dataclass-моделями с `slots=True`;
  неизменяемые DTO используют `frozen=True`, неоднозначные аргументы — `kw_only=True`.
- Порты принадлежат application, используют `Protocol` и `@abstractmethod`.
  Адаптер может реализовывать несколько узких портов; зависимости собирает `main/di.py`.
- Возвращающий себя метод или фабрика использует `Self`. Проверку обеспечивает
  `scripts/makefile/self_return.py`, заимствованный из референса с MIT-уведомлением
  в [licenses/fastapi-clean-example.txt](../licenses/fastapi-clean-example.txt).
- `Any`, отложенные аннотации и `TYPE_CHECKING` запрещены настройками Ruff.
  Для типов используются порядок объявлений, `Self` и необходимые явные forward references.
  Широкий `object`, словарный `.get()`, `noqa` и `type: ignore` не используются
  как способ обхода типизации; эти ограничения дополнительно проверяются при ревью.
- Пустые `__init__.py` не содержат реэкспортов или запуска кода.
- CLI остаётся синхронным. Внешние команды ограничены временем; порядок запуска,
  блокировка, обработка отмены и владение созданными ресурсами описаны в
  [архитектуре](architecture.md).

Ruff сохраняет существующий строгий профиль `ALL`. mypy проверяет `src`, `tests`,
`scripts` и весь Python-код `infra`, включая оба гостевых скрипта. Профиль не
использует `ignore_missing_imports` и не исключает тесты из типизации.
JSON проверяется на границе адаптера: декларация `TypedDict` описывает форму,
но сама по себе не является runtime-валидацией данных Hermes.

## Shell и Makefile

Makefile задаёт Bash, `-eu -o pipefail`, цель по умолчанию `check` и aliases
для помощников. Shell-скрипты в `scripts/makefile` начинаются с `#!/bin/bash`,
комментария о запуске из Makefile и `set -eu -o pipefail`. Отступ — два пробела;
аргументы и пути передаются с корректным quoting. `scripts/lab.sh` сохраняет
переносимый shebang `#!/usr/bin/env bash` и прежние девять команд стенда.

`shellcheck.sh` проверяет синтаксис всех `.sh` и запускает ShellCheck.
`slotscheck.sh` передаёт пути исходников и сохраняет ненулевой код проверки.
`pip_audit.sh` экспортирует закреплённые зависимости с хешами во временный файл,
проверяет их и удаляет только собственный файл. Ошибка аудита возвращается вызывающему.
`pycache_del.sh` удаляет `.pyc`, `.pyo` и пустые `__pycache__` только в
`src`, `tests`, `scripts`, `infra`.

## Команды

После `uv sync --locked --group dev`:

| Команда | Результат |
| --- | --- |
| `make` / `make check` / `make check-ci` | Все статические проверки и все тесты |
| `make lint` | Ruff, TOML, зависимости, shell, slots, Self, импорты и mypy |
| `make format` | Безопасные исправления Ruff и форматирование Python/TOML |
| `make test` | Весь pytest и отчёт покрытия в `htmlcov/index.html` |
| `make shellcheck` | Bash-синтаксис и ShellCheck всех shell-скриптов |
| `make slotscheck` | Импорты и корректность slots для `src`, `infra`, `scripts` |
| `make pip-audit` | Отдельный сетевой аудит закреплённых dev-зависимостей |
| `make pycache-del` | Очистка Python-кеша исходников проекта |
| `make hooks` | Установка локального pre-commit hook через prek |

Проверки `check` и `check-ci` исходники не исправляют. pytest запускает все
тесты; маркеры не скрывают отдельные группы. Отчёт покрытия относится к процессу
pytest: он не измеряет выполнение Hermes или дочернего CLI в настоящей VM.

Тесты управления macOS/Lima используют отдельный HOME и подменённые внешние
команды; тесты PTY и файлов используют настоящие временные ресурсы. `preflight.py`
проверяется с искусственными Telegram-значениями без подключения бота или модели.

## Hooks и CI

`.pre-commit-config.yaml` запускает `make check-ci` и проверки форматов файлов.
Сохранённые тексты задания и подтверждения подготовки не исправляются hooks.
Аудит зависимостей запускается вручную:

```sh
uv run --locked prek run --stage manual pip-audit-local
```

GitHub Actions использует Python 3.13 на macOS, устанавливает зависимости
через `uv sync --locked`, запускает `make check-ci` и файловые hooks.
Запуск workflow на GitHub проверяется после публикации изменений.

Первичные описания дополнительных проверок:
[deptry](https://deptry.com/usage/),
[slotscheck](https://github.com/ariebovenberg/slotscheck),
[Tombi](https://tombi-toml.github.io/tombi/docs/cli/linter/).

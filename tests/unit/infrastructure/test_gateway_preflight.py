from pathlib import Path

import pytest

from infra.hermes.preflight import (
    GatewayConfiguration,
    ModelConfiguration,
    TelegramConfiguration,
    TelegramExtra,
    check_model,
    check_telegram,
    read_private_environment,
)


@pytest.mark.parametrize(
    ("provider", "endpoint", "context_length", "fallback_enabled", "message"),
    [
        ("cloud", "http://127.0.0.1:11434/v1", 65536, False, "local Ollama endpoint"),
        ("custom", "https://example.invalid/v1", 65536, False, "local Ollama endpoint"),
        ("custom", "http://127.0.0.1:11434/v1", 65536, True, "Cloud fallback"),
        ("custom", "http://127.0.0.1:11434/v1", 63999, False, "context is below"),
    ],
)
def test_preflight_rejects_unapproved_model(
    provider: str, endpoint: str, context_length: int, message: str, *, fallback_enabled: bool
) -> None:
    configuration = GatewayConfiguration(
        model=ModelConfiguration(provider=provider, base_url=endpoint, context_length=context_length),
        fallback_enabled=fallback_enabled,
        telegram=TelegramConfiguration(enabled=True),
    )

    with pytest.raises(ValueError, match=message):
        check_model(configuration)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("TELEGRAM_ALLOWED_USERS", "42,43", "own numeric"),
        ("TELEGRAM_BOT_TOKEN", "", "dedicated bot token"),
        ("TELEGRAM_ALLOW_ALL", "true", "TELEGRAM_ALLOW_ALL must be explicitly disabled"),
        ("TELEGRAM_GUEST_MODE", "true", "TELEGRAM_GUEST_MODE must be explicitly disabled"),
        ("TELEGRAM_GROUP_ALLOWED_CHATS", "43", "without group access"),
    ],
)
def test_preflight_rejects_missing_or_broad_telegram_access(field: str, value: str, message: str) -> None:
    environment = {"TELEGRAM_ALLOWED_USERS": "42", "TELEGRAM_BOT_TOKEN": "123:fixture"}
    environment[field] = value

    with pytest.raises(ValueError, match=message):
        check_telegram(TelegramConfiguration(enabled=True), environment)


def test_preflight_accepts_local_model_and_private_owner(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text(
        "# Only fixture values\n"
        "TELEGRAM_ALLOWED_USERS='42'\n"
        "TELEGRAM_BOT_TOKEN=123:fixture # comment\n"
        "TELEGRAM_ALLOW_ALL=false\n"
        "TELEGRAM_GUEST_MODE=no\n",
    )
    configuration = GatewayConfiguration(
        model=ModelConfiguration(provider="custom", base_url="http://127.0.0.1:11434/v1", context_length=65536),
        fallback_enabled=False,
        telegram=TelegramConfiguration(enabled=True, extra=TelegramExtra(allow_from=["42"])),
    )

    check_model(configuration)
    check_telegram(configuration.telegram, read_private_environment(tmp_path))


@pytest.mark.parametrize(
    ("telegram", "message"),
    [
        (TelegramConfiguration(enabled=False), "Enable the Telegram platform"),
        (TelegramConfiguration(enabled=True, extra=TelegramExtra(guest_mode=True)), "guest mode is forbidden"),
        (TelegramConfiguration(enabled=True, extra=TelegramExtra(allow_from=["43"])), "Unexpected Telegram access"),
    ],
)
def test_preflight_rejects_unsafe_gateway_configuration(telegram: TelegramConfiguration, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        check_telegram(telegram, {"TELEGRAM_ALLOWED_USERS": "42", "TELEGRAM_BOT_TOKEN": "123:fixture"})

import json
from pathlib import Path

import pytest

from infra.hermes import preflight
from infra.hermes.preflight import (
    ApiConfiguration,
    ApiExtra,
    GatewayConfiguration,
    ModelConfiguration,
    TelegramConfiguration,
    TelegramExtra,
    check_api,
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
        api=ApiConfiguration(enabled=True, extra=ApiExtra(host="127.0.0.1", port=8642)),
    )

    with pytest.raises(ValueError, match=message):
        check_model(configuration)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("TELEGRAM_ALLOWED_USERS", "42,43", "own numeric"),
        ("TELEGRAM_BOT_TOKEN", "", "dedicated bot token"),
        ("TELEGRAM_ALLOW_ALL", "true", "TELEGRAM_ALLOW_ALL must be explicitly disabled"),
        ("TELEGRAM_ALLOW_ALL_USERS", "true", "TELEGRAM_ALLOW_ALL_USERS must be explicitly disabled"),
        ("GATEWAY_ALLOW_ALL_USERS", "true", "GATEWAY_ALLOW_ALL_USERS must be explicitly disabled"),
        ("GATEWAY_ALLOWED_USERS", "43", "Global allowlist must be empty or contain only the owner"),
        ("GATEWAY_ALLOWED_USERS", "*", "Global allowlist must be empty or contain only the owner"),
        ("TELEGRAM_GUEST_MODE", "true", "TELEGRAM_GUEST_MODE must be explicitly disabled"),
        ("TELEGRAM_GROUP_ALLOWED_CHATS", "43", "without group access"),
    ],
)
def test_preflight_rejects_missing_or_broad_telegram_access(field: str, value: str, message: str) -> None:
    environment = {"TELEGRAM_ALLOWED_USERS": "42", "TELEGRAM_BOT_TOKEN": "123:fixture"}
    environment[field] = value

    with pytest.raises(ValueError, match=message):
        check_telegram(TelegramConfiguration(enabled=False), environment)


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
        telegram=TelegramConfiguration(enabled=False, extra=TelegramExtra(allow_from=["42"])),
        api=ApiConfiguration(enabled=True, extra=ApiExtra(host="127.0.0.1", port=8642)),
    )

    check_model(configuration)
    check_telegram(configuration.telegram, read_private_environment(tmp_path))


@pytest.mark.parametrize(
    ("telegram", "message"),
    [
        (TelegramConfiguration(enabled=True), "Disable the native Telegram adapter"),
        (TelegramConfiguration(enabled=False, extra=TelegramExtra(guest_mode=True)), "guest mode is forbidden"),
        (TelegramConfiguration(enabled=False, extra=TelegramExtra(allow_from=["43"])), "Unexpected Telegram access"),
        (
            TelegramConfiguration(enabled=False, extra=TelegramExtra(unauthorized_dm_behavior="pair")),
            "Unauthorized Telegram DMs must be ignored",
        ),
    ],
)
def test_preflight_rejects_unsafe_gateway_configuration(telegram: TelegramConfiguration, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        check_telegram(telegram, {"TELEGRAM_ALLOWED_USERS": "42", "TELEGRAM_BOT_TOKEN": "123:fixture"})


def test_private_environment_preserves_global_access_controls(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("GATEWAY_ALLOW_ALL_USERS=true\nGATEWAY_ALLOWED_USERS=43\n")

    assert read_private_environment(tmp_path) == {"GATEWAY_ALLOW_ALL_USERS": "true", "GATEWAY_ALLOWED_USERS": "43"}


@pytest.mark.parametrize("allow_all", [False, True])
def test_preflight_checks_global_configuration(monkeypatch: pytest.MonkeyPatch, *, allow_all: bool) -> None:
    responses = {
        "model": json.dumps({"provider": "custom", "base_url": "http://127.0.0.1:11434/v1", "context_length": 65536}),
        "fallback_providers": "[]",
        "gateway": json.dumps({"allow_all_users": allow_all}),
        "platforms.telegram": json.dumps({"enabled": False}),
        "platforms.api_server": json.dumps({"enabled": True, "extra": {"host": "127.0.0.1", "port": 8642}}),
    }

    def read_configuration(field: str) -> str:
        return responses[field]

    monkeypatch.setattr(preflight, "read_configuration", read_configuration)

    if allow_all:
        with pytest.raises(ValueError, match="Global allow-all must be disabled"):
            preflight.load_gateway_configuration()
    else:
        configuration = preflight.load_gateway_configuration()
        check_model(configuration)
        check_telegram(configuration.telegram, {"TELEGRAM_ALLOWED_USERS": "42", "TELEGRAM_BOT_TOKEN": "123:fixture"})


@pytest.mark.parametrize("enabled", [False, True])
def test_preflight_uses_telegram_section_written_by_setup(monkeypatch: pytest.MonkeyPatch, *, enabled: bool) -> None:
    responses = {
        "model": json.dumps({"provider": "custom", "base_url": "http://127.0.0.1:11434/v1", "context_length": 65536}),
        "fallback_providers": "[]",
        "gateway": json.dumps({"allow_all_users": False, "platforms": {"telegram": {"enabled": not enabled}}}),
        "platforms.telegram": json.dumps({"enabled": enabled, "extra": {"unauthorized_dm_behavior": "ignore"}}),
        "platforms.api_server": json.dumps({"enabled": True, "extra": {"host": "127.0.0.1", "port": 8642}}),
    }

    def read_configuration(field: str) -> str:
        return responses[field]

    monkeypatch.setattr(preflight, "read_configuration", read_configuration)

    configuration = preflight.load_gateway_configuration()

    assert configuration.telegram["enabled"] is enabled


@pytest.mark.parametrize(
    ("host", "backend_key", "bot_key", "legacy_token", "message"),
    [
        ("192.0.2.10", "fixture" * 8, "fixture" * 8, "", "only on VM loopback"),
        ("127.0.0.1", "short", "short", "", "strong private"),
        ("127.0.0.1", "fixture" * 8, "different" * 8, "", "share the private"),
        ("127.0.0.1", "fixture" * 8, "fixture" * 8, "123:fixture", "only in the custom"),
    ],
)
def test_preflight_rejects_exposed_api_or_duplicate_telegram_owner(
    host: str, backend_key: str, bot_key: str, legacy_token: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        check_api(
            ApiConfiguration(enabled=True, extra=ApiExtra(host=host, port=8642)),
            {"API_SERVER_KEY": backend_key, "TELEGRAM_BOT_TOKEN": legacy_token},
            {"HERMES_API_KEY": bot_key},
        )

"""Refuse gateway startup until the local model and private Telegram setup are explicit."""

import hmac
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, NotRequired, TypedDict

CONFIG_TIMEOUT: Final = 30.0
MIN_CONTEXT_LENGTH: Final = 64000
LOCAL_MODEL_ENDPOINT: Final = "http://127.0.0.1:11434/v1"
LOCAL_API_PORT: Final = 8642
MIN_API_KEY_LENGTH: Final = 32


class ModelConfiguration(TypedDict):
    provider: str
    base_url: str
    context_length: int


class TelegramExtra(TypedDict, total=False):
    guest_mode: bool
    unauthorized_dm_behavior: str
    allow_from: list[str]
    group_allow_from: list[str]
    group_allowed_chats: list[str]


class TelegramConfiguration(TypedDict):
    enabled: bool
    extra: NotRequired[TelegramExtra]


class GatewaySettings(TypedDict):
    allow_all_users: bool


class ApiExtra(TypedDict):
    host: str
    port: int


class ApiConfiguration(TypedDict):
    enabled: bool
    extra: ApiExtra


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayConfiguration:
    model: ModelConfiguration
    fallback_enabled: bool
    telegram: TelegramConfiguration
    api: ApiConfiguration


def read_configuration(
    field: Literal["model", "fallback_providers", "gateway", "platforms.telegram", "platforms.api_server"],
) -> str:
    # Hermes interprets YAML in its managed runtime; standalone Python lacks PyYAML.
    executable = shutil.which("hermes")
    if executable is None:
        raise FileNotFoundError("Hermes CLI is not available in this image.")
    result = subprocess.run(
        (executable, "config", "get", "--json", field),
        capture_output=True,
        text=True,
        timeout=CONFIG_TIMEOUT,
        check=True,
    )
    return result.stdout


def load_gateway_configuration() -> GatewayConfiguration:
    model: ModelConfiguration = json.loads(read_configuration("model"))
    fallback_enabled = bool(json.loads(read_configuration("fallback_providers")))
    gateway: GatewaySettings = json.loads(read_configuration("gateway"))
    if gateway["allow_all_users"]:
        raise ValueError("Global allow-all must be disabled in gateway configuration.")
    telegram: TelegramConfiguration = json.loads(read_configuration("platforms.telegram"))
    api: ApiConfiguration = json.loads(read_configuration("platforms.api_server"))
    return GatewayConfiguration(model=model, fallback_enabled=fallback_enabled, telegram=telegram, api=api)


def check_model(configuration: GatewayConfiguration) -> None:
    model = configuration.model
    if model["provider"] != "custom" or model["base_url"] != LOCAL_MODEL_ENDPOINT:
        raise ValueError("Only the explicitly selected local Ollama endpoint is allowed.")
    if configuration.fallback_enabled:
        raise ValueError("Cloud fallback has not been authorized.")
    if model["context_length"] < MIN_CONTEXT_LENGTH:
        raise ValueError("Configured context is below the assignment requirement.")


def read_private_environment(data: Path) -> dict[str, str]:
    # Parse gateway access values without executing the private .env.
    environment: dict[str, str] = {}
    for line in (data / ".env").read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        field, raw_value = line.split("=", 1)
        field = field.strip()
        if field.startswith(("TELEGRAM_", "GATEWAY_", "API_SERVER_", "HERMES_API_KEY")):
            parts = shlex.split(raw_value, comments=True)
            if len(parts) > 1:
                raise ValueError("Invalid gateway value in private .env.")
            environment[field] = parts[0] if parts else ""
    return environment


def check_telegram(telegram: TelegramConfiguration, environment: dict[str, str]) -> None:
    environment = {
        "TELEGRAM_ALLOWED_USERS": "",
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_ALLOW_ALL": "false",
        "TELEGRAM_ALLOW_ALL_USERS": "false",
        "GATEWAY_ALLOW_ALL_USERS": "false",
        "GATEWAY_ALLOWED_USERS": "",
        "TELEGRAM_GUEST_MODE": "false",
        "TELEGRAM_GROUP_ALLOWED_USERS": "",
        "TELEGRAM_GROUP_ALLOWED_CHATS": "",
        **environment,
    }
    user_id = environment["TELEGRAM_ALLOWED_USERS"]
    token = environment["TELEGRAM_BOT_TOKEN"]
    if not user_id or not re.fullmatch(r"[1-9][0-9]*", user_id):
        raise ValueError("Set exactly your own numeric TELEGRAM_ALLOWED_USERS in the private .env.")
    if not token or not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token):
        raise ValueError("Set the dedicated bot token in the private .env.")
    for field in ("TELEGRAM_ALLOW_ALL", "TELEGRAM_ALLOW_ALL_USERS", "GATEWAY_ALLOW_ALL_USERS", "TELEGRAM_GUEST_MODE"):
        value = environment[field]
        if value.lower() not in {"false", "0", "no"}:
            raise ValueError(f"{field} must be explicitly disabled.")
    if environment["GATEWAY_ALLOWED_USERS"] not in ("", user_id):
        raise ValueError("Global allowlist must be empty or contain only the owner.")
    for field in ("TELEGRAM_GROUP_ALLOWED_USERS", "TELEGRAM_GROUP_ALLOWED_CHATS"):
        if environment[field]:
            raise ValueError("This lab permits only the owner, without group access.")
    check_telegram_platform(telegram, user_id)


def check_telegram_platform(telegram: TelegramConfiguration, user_id: str) -> None:
    if telegram["enabled"]:
        raise ValueError("Disable the native Telegram adapter before starting the custom bot.")
    extra = TelegramExtra(guest_mode=False, unauthorized_dm_behavior="ignore")
    if "extra" in telegram:
        extra.update(telegram["extra"])
    if extra["guest_mode"]:
        raise ValueError("Telegram guest mode is forbidden for this lab.")
    if extra["unauthorized_dm_behavior"] != "ignore":
        raise ValueError("Unauthorized Telegram DMs must be ignored.")
    access_field: Literal["allow_from", "group_allow_from", "group_allowed_chats"]
    for access_field in ("allow_from", "group_allow_from", "group_allowed_chats"):
        if access_field in extra and extra[access_field] not in ([], [user_id]):
            raise ValueError(f"Unexpected Telegram access in {access_field}.")


def check_api(api: ApiConfiguration, backend: dict[str, str], bot: dict[str, str]) -> None:
    if not api["enabled"] or api["extra"]["host"] != "127.0.0.1" or api["extra"]["port"] != LOCAL_API_PORT:
        raise ValueError("Enable the Hermes API only on VM loopback port 8642.")
    if "API_SERVER_KEY" not in backend or len(backend["API_SERVER_KEY"]) < MIN_API_KEY_LENGTH:
        raise ValueError("A strong private Hermes API key is required.")
    if "HERMES_API_KEY" not in bot or not hmac.compare_digest(backend["API_SERVER_KEY"], bot["HERMES_API_KEY"]):
        raise ValueError("The bot and Hermes must share the private API key.")
    if backend.get("TELEGRAM_BOT_TOKEN"):
        raise ValueError("Keep Telegram credentials only in the custom bot environment.")


def main() -> int:
    try:
        configuration = load_gateway_configuration()
        check_model(configuration)
        backend = read_private_environment(Path("/opt/data"))
        bot = read_private_environment(Path("/opt/bot"))
        check_telegram(configuration.telegram, bot)
        check_api(configuration.api, backend, bot)
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"Gateway is not ready: {error}", file=sys.stderr)
        return 1
    print("Gateway configuration passed local preflight. Test outsider rejection separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

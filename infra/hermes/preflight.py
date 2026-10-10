"""Refuse gateway startup until the local model and private Telegram setup are explicit."""

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


class ModelConfiguration(TypedDict):
    provider: str
    base_url: str
    context_length: int


class TelegramExtra(TypedDict, total=False):
    guest_mode: bool
    allow_from: list[str]
    group_allow_from: list[str]
    group_allowed_chats: list[str]


class TelegramConfiguration(TypedDict):
    enabled: bool
    extra: NotRequired[TelegramExtra]


@dataclass(frozen=True, slots=True, kw_only=True)
class GatewayConfiguration:
    model: ModelConfiguration
    fallback_enabled: bool
    telegram: TelegramConfiguration


def read_configuration(field: Literal["model", "fallback_providers", "gateway.platforms.telegram"]) -> str:
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
    telegram: TelegramConfiguration = json.loads(read_configuration("gateway.platforms.telegram"))
    return GatewayConfiguration(model=model, fallback_enabled=fallback_enabled, telegram=telegram)


def check_model(configuration: GatewayConfiguration) -> None:
    model = configuration.model
    if model["provider"] != "custom" or model["base_url"] != LOCAL_MODEL_ENDPOINT:
        raise ValueError("Only the explicitly selected local Ollama endpoint is allowed.")
    if configuration.fallback_enabled:
        raise ValueError("Cloud fallback has not been authorized.")
    if model["context_length"] < MIN_CONTEXT_LENGTH:
        raise ValueError("Configured context is below the assignment requirement.")


def read_private_environment(data: Path) -> dict[str, str]:
    # Parse Telegram's string values without executing the private .env.
    environment: dict[str, str] = {}
    for line in (data / ".env").read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        field, raw_value = line.split("=", 1)
        field = field.strip()
        if field.startswith("TELEGRAM_"):
            parts = shlex.split(raw_value, comments=True)
            if len(parts) > 1:
                raise ValueError("Invalid Telegram value in private .env.")
            environment[field] = parts[0] if parts else ""
    return environment


def check_telegram(telegram: TelegramConfiguration, environment: dict[str, str]) -> None:
    environment = {
        "TELEGRAM_ALLOWED_USERS": "",
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_ALLOW_ALL": "false",
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
    for field in ("TELEGRAM_ALLOW_ALL", "TELEGRAM_GUEST_MODE"):
        value = environment[field]
        if value.lower() not in {"false", "0", "no"}:
            raise ValueError(f"{field} must be explicitly disabled.")
    for field in ("TELEGRAM_GROUP_ALLOWED_USERS", "TELEGRAM_GROUP_ALLOWED_CHATS"):
        if environment[field]:
            raise ValueError("This lab permits only the owner, without group access.")
    if not telegram["enabled"]:
        raise ValueError("Enable the Telegram platform only after the private setup is complete.")
    extra = TelegramExtra(guest_mode=False)
    if "extra" in telegram:
        extra.update(telegram["extra"])
    if extra["guest_mode"]:
        raise ValueError("Telegram guest mode is forbidden for this lab.")
    access_field: Literal["allow_from", "group_allow_from", "group_allowed_chats"]
    for access_field in ("allow_from", "group_allow_from", "group_allowed_chats"):
        if access_field in extra and extra[access_field] not in ([], [user_id]):
            raise ValueError(f"Unexpected Telegram access in {access_field}.")


def main() -> int:
    try:
        configuration = load_gateway_configuration()
        check_model(configuration)
        check_telegram(configuration.telegram, read_private_environment(Path("/opt/data")))
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"Gateway is not ready: {error}", file=sys.stderr)
        return 1
    print("Gateway configuration passed local preflight. Test outsider rejection separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

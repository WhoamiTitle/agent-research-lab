import os
import re
from dataclasses import dataclass
from pathlib import Path

from agent_bot.adapters.hermes.config import HermesConfig
from agent_bot.entities.owner import Owner
from agent_bot.presentation.telegram.config import TelegramConfig

MIN_API_KEY_LENGTH = 32


@dataclass(frozen=True, slots=True, kw_only=True)
class Config:
    telegram: TelegramConfig
    hermes: HermesConfig
    owner: Owner
    data_directory: Path = Path("/opt/bot")
    timezone: str = "America/Los_Angeles"


def load_config() -> Config:
    try:
        token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
        owner = os.environ["TELEGRAM_ALLOWED_USERS"].strip()
        api_key = os.environ["HERMES_API_KEY"].strip()
    except KeyError as error:
        raise ValueError(f"Missing private bot setting: {error.args[0]}.") from None
    if re.fullmatch(r"[1-9][0-9]*", owner) is None:
        raise ValueError("Exactly one numeric Telegram owner is required.")
    if not token or len(api_key) < MIN_API_KEY_LENGTH:
        raise ValueError("A bot token and a strong Hermes API key are required.")
    return Config(
        telegram=TelegramConfig(token=token),
        hermes=HermesConfig(api_key=api_key),
        owner=Owner(user_id=int(owner)),
    )

from dishka import Provider, Scope, from_context

from agent_bot.adapters.hermes.config import HermesConfig
from agent_bot.entities.owner import Owner
from agent_bot.presentation.telegram.config import TelegramConfig


class ConfigProvider(Provider):
    scope = Scope.APP
    configs = from_context(HermesConfig) + from_context(Owner) + from_context(TelegramConfig)

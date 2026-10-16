from dishka import STRICT_VALIDATION, AsyncContainer, make_async_container

from agent_bot.adapters.hermes.config import HermesConfig
from agent_bot.entities.owner import Owner
from agent_bot.main.config.loader import Config
from agent_bot.main.di.providers.adapter import AdapterProvider
from agent_bot.main.di.providers.config import ConfigProvider
from agent_bot.main.di.providers.interactor import InteractorProvider
from agent_bot.presentation.telegram.config import TelegramConfig


def get_async_container(config: Config) -> AsyncContainer:
    return make_async_container(
        ConfigProvider(),
        AdapterProvider(),
        InteractorProvider(),
        context={HermesConfig: config.hermes, Owner: config.owner, TelegramConfig: config.telegram},
        validation_settings=STRICT_VALIDATION,
    )

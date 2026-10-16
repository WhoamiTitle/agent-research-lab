import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand
from dishka.integrations.aiogram import setup_dishka

from agent_bot.application.common.agent import AgentGateway, AgentUnavailableError
from agent_bot.main.config.loader import Config, load_config
from agent_bot.main.di.container import get_async_container
from agent_bot.main.lock import BotAlreadyRunningError, single_process
from agent_bot.main.logs import configure_logging
from agent_bot.presentation.telegram.handlers import create_router

logger = logging.getLogger(__name__)


async def run_bot(config: Config) -> None:
    with single_process(config.data_directory):
        container = get_async_container(config)
        try:
            bot = await container.get(Bot)
            agent = await container.get(AgentGateway)
            if not await agent.is_ready():
                raise AgentUnavailableError
            await bot.get_me()
            await bot.set_my_commands(
                [
                    BotCommand(command="start", description="Начать работу"),
                    BotCommand(command="help", description="Справка"),
                    BotCommand(command="status", description="Доступность Hermes"),
                ],
            )
            dispatcher = Dispatcher(disable_fsm=True)
            dispatcher.include_router(create_router())
            setup_dishka(container=container, router=dispatcher)
            logger.info("bot_polling_started")
            try:
                await dispatcher.start_polling(
                    bot,
                    allowed_updates=["message"],
                    handle_as_tasks=False,
                    close_bot_session=False,
                    polling_timeout=10,
                )
            finally:
                logger.info("bot_polling_stopped")
        finally:
            await container.close()


def main() -> None:
    try:
        config = load_config()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    configure_logging(config.timezone)
    try:
        asyncio.run(run_bot(config))
    except (AgentUnavailableError, TelegramAPIError, BotAlreadyRunningError, TimeoutError):
        logger.exception("bot_startup_failed")
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        logger.info("bot_interrupted")

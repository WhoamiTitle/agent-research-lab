from collections.abc import AsyncIterator

import httpx
from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession
from dishka import Provider, Scope, WithParents, provide

from agent_bot.adapters.hermes.config import HermesConfig
from agent_bot.adapters.hermes.gateway import HermesGatewayImpl
from agent_bot.presentation.telegram.config import TelegramConfig


class AdapterProvider(Provider):
    scope = Scope.APP
    gateway = provide(WithParents[HermesGatewayImpl])

    @provide
    async def http_client(self, config: HermesConfig) -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(
            base_url=config.base_url,
            headers={"Authorization": f"Bearer {config.api_key}"},
            timeout=config.request_timeout,
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=2),
            trust_env=False,
        ) as client:
            yield client

    @provide
    async def telegram_bot(self, config: TelegramConfig) -> AsyncIterator[Bot]:
        bot = Bot(token=config.token, session=AiohttpSession(timeout=15))
        try:
            yield bot
        finally:
            await bot.session.close()

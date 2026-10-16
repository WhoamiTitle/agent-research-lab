import asyncio
import socket
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.types import Chat, Message, Update, User
from aiohttp import web
from dishka import Provider, Scope, from_context, make_async_container
from dishka.integrations.aiogram import setup_dishka

from agent_bot.application.common.agent import AgentGateway
from agent_bot.entities.owner import Owner
from agent_bot.main.di.providers.interactor import InteractorProvider
from agent_bot.presentation.telegram.handlers import create_router

TELEGRAM_TEXT_LIMIT: Final = 4096
DUMMY_BOT_CREDENTIAL: Final = "123:fixture"


@dataclass(slots=True)
class AgentMock(AgentGateway):
    reply: str = "Контрольный ответ"
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def answer(self, text: str, *, request_id: str) -> str:
        self.calls.append((text, request_id))
        await asyncio.sleep(0)
        return self.reply

    async def is_ready(self) -> bool:
        await asyncio.sleep(0)
        return True


class MessageProvider(Provider):
    scope = Scope.APP
    owner = from_context(Owner)
    agent = from_context(AgentGateway)


@dataclass(frozen=True, slots=True, kw_only=True)
class TelegramFixture:
    dispatcher: Dispatcher
    bot: Bot
    agent: AgentMock
    replies: list[str]

    async def send(self, text: str, *, sender: int = 42, chat_type: str = "private") -> None:
        await self.dispatcher.feed_update(
            self.bot,
            Update(
                update_id=11,
                message=Message(
                    message_id=7,
                    date=datetime(2026, 10, 16, tzinfo=UTC),
                    chat=Chat(id=sender, type=chat_type),
                    from_user=User(id=sender, is_bot=False, first_name="Fixture"),
                    text=text,
                ),
            ),
        )


@pytest_asyncio.fixture
async def telegram() -> AsyncIterator[TelegramFixture]:
    replies: list[str] = []

    async def receive(request: web.Request) -> web.Response:
        form = await request.post()
        replies.append(str(form["text"]))
        return web.json_response(
            {
                "ok": True,
                "result": {
                    "message_id": len(replies),
                    "date": 1000,
                    "chat": {"id": int(str(form["chat_id"])), "type": "private"},
                    "text": replies[-1],
                },
            },
        )

    application = web.Application()
    application.router.add_post("/bot{token}/sendMessage", receive)
    runner = web.AppRunner(application)
    await runner.setup()
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.settimeout(0)
    site = web.SockSite(runner, listener)
    await site.start()
    api = TelegramAPIServer.from_base(f"http://127.0.0.1:{listener.getsockname()[1]}")
    bot = Bot(token=DUMMY_BOT_CREDENTIAL, session=AiohttpSession(api=api))
    agent = AgentMock()
    container = make_async_container(
        MessageProvider(), InteractorProvider(), context={Owner: Owner(user_id=42), AgentGateway: agent}
    )
    dispatcher = Dispatcher(disable_fsm=True)
    dispatcher.include_router(create_router())
    setup_dishka(container=container, router=dispatcher)
    try:
        yield TelegramFixture(dispatcher=dispatcher, bot=bot, agent=agent, replies=replies)
    finally:
        await container.close()
        await bot.session.close()
        await runner.cleanup()


async def test_start_replies_without_calling_model(telegram: TelegramFixture) -> None:
    await telegram.send("/start")

    assert len(telegram.replies) == 1
    assert "Agent Research Lab" in telegram.replies[0]
    assert telegram.agent.calls == []


@pytest.mark.parametrize(("sender", "chat_type"), [(43, "private"), (42, "group")])
async def test_outsider_and_group_do_not_reach_hermes_or_receive_reply(
    telegram: TelegramFixture, sender: int, chat_type: str
) -> None:
    await telegram.send("Контрольный вопрос", sender=sender, chat_type=chat_type)

    assert telegram.replies == []
    assert telegram.agent.calls == []


async def test_prompt_is_forwarded_and_long_unicode_reply_is_delivered(telegram: TelegramFixture) -> None:
    telegram.agent.reply = "😀" * 3000

    await telegram.send("Контрольный вопрос")

    assert telegram.agent.calls == [("Контрольный вопрос", "telegram-11")]
    assert "".join(telegram.replies) == telegram.agent.reply
    assert all(len(part.encode("utf-16-le")) // 2 <= TELEGRAM_TEXT_LIMIT for part in telegram.replies)


async def test_status_does_not_run_model(telegram: TelegramFixture) -> None:
    await telegram.send("/status")

    assert telegram.replies == ["Hermes доступен. Модель: локальная Ollama."]
    assert telegram.agent.calls == []

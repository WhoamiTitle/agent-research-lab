import logging

from aiogram import Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, Update
from dishka.integrations.aiogram import FromDishka, inject

from agent_bot.application.handle_message import HandleMessage, MessageKind, MessageRequest

logger = logging.getLogger(__name__)
REPLY_CHUNK_SIZE = 2000  # At most 4000 UTF-16 units, including supplementary characters.


def classify_message(text: str | None) -> MessageKind:
    if text is None:
        return MessageKind.UNSUPPORTED
    command = text.split(maxsplit=1)[0].partition("@")[0] if text.strip() else ""
    match command:
        case "/start":
            return MessageKind.START
        case "/help":
            return MessageKind.HELP
        case "/status":
            return MessageKind.STATUS
        case _:
            return MessageKind.UNSUPPORTED if command.startswith("/") else MessageKind.TEXT


@inject
async def handle_message(
    message: Message,
    event_update: Update,
    interactor: FromDishka[HandleMessage],
) -> None:
    request = MessageRequest(
        sender_id=message.from_user.id if message.from_user is not None else None,
        private_chat=message.chat.type == ChatType.PRIVATE,
        kind=classify_message(message.text),
        text=message.text or "",
        request_id=f"telegram-{event_update.update_id}",
    )
    reply = await interactor.execute(request)
    if reply is None:
        logger.info("update_rejected")
        return
    try:
        for offset in range(0, len(reply), REPLY_CHUNK_SIZE):
            await message.answer(reply[offset : offset + REPLY_CHUNK_SIZE], parse_mode=None)
    except TelegramAPIError:
        logger.exception("telegram_delivery_failed")
        return
    logger.info("reply_sent")


def create_router() -> Router:
    router = Router(name="agent_lab")
    router.message.register(handle_message)
    return router

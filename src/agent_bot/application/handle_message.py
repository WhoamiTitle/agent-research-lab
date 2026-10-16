from dataclasses import dataclass
from enum import StrEnum

from agent_bot.application.common.agent import (
    AgentApprovalRequiredError,
    AgentError,
    AgentGateway,
    AgentTimedOutError,
)
from agent_bot.entities.owner import Owner


class MessageKind(StrEnum):
    START = "start"
    HELP = "help"
    STATUS = "status"
    TEXT = "text"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True, kw_only=True)
class MessageRequest:
    sender_id: int | None
    private_chat: bool
    kind: MessageKind
    text: str
    request_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class HandleMessage:
    owner: Owner
    agent: AgentGateway

    async def execute(self, request: MessageRequest) -> str | None:
        if not self.owner.permits(request.sender_id, private_chat=request.private_chat):
            return None
        try:
            return await self._execute_authorized(request)
        except AgentApprovalRequiredError:
            return (
                "Hermes запросил подтверждение действия. Отправлен запрос остановки. "
                "Подтверждения в этом боте пока недоступны."
            )
        except AgentTimedOutError:
            return "Время ожидания Hermes истекло. Отправлен запрос остановки; проверь состояние перед повтором."
        except AgentError:
            return "Сбой получения ответа Hermes. Проверь состояние через /status."

    async def _execute_authorized(self, request: MessageRequest) -> str:
        match request.kind:
            case MessageKind.START | MessageKind.HELP:
                return (
                    "Это бот лаборатории Agent Research Lab.\n"
                    "Отправь текстовый вопрос: Hermes обработает запрос через локальную Ollama.\n"
                    "/status — доступность агента; /help — эта справка."
                )
            case MessageKind.STATUS:
                ready = await self.agent.is_ready()
                return "Hermes доступен. Модель: локальная Ollama." if ready else "Hermes пока недоступен."
            case MessageKind.TEXT:
                if request.text.strip():
                    return await self.agent.answer(request.text, request_id=request.request_id)
            case MessageKind.UNSUPPORTED:
                pass
        return "Отправь текстовый вопрос или используй /help."

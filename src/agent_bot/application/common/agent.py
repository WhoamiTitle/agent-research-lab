from abc import abstractmethod
from typing import Protocol


class AgentError(Exception):
    pass


class AgentUnavailableError(AgentError):
    pass


class AgentFailedError(AgentError):
    pass


class AgentTimedOutError(AgentError):
    pass


class AgentApprovalRequiredError(AgentError):
    pass


class AgentGateway(Protocol):
    @abstractmethod
    async def answer(self, text: str, *, request_id: str) -> str: ...

    @abstractmethod
    async def is_ready(self) -> bool: ...

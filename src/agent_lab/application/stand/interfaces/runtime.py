from abc import abstractmethod
from contextlib import AbstractContextManager
from typing import Protocol

from agent_lab.application.stand.components import StandComponent


class StandStartup(Protocol):
    """Bounded lifecycle operations; failures raise StandOperationError.

    Hold the exclusive lock from inspection through readiness or rollback.
    A component absent before start belongs to this invocation, including when
    start fails after creating it. Loaded but unhealthy services are reused;
    readiness must fail rather than restart them. Stop preserves persistent data.
    """

    @abstractmethod
    def exclusive(self) -> AbstractContextManager[None]: ...

    @abstractmethod
    def is_started(self, component: StandComponent) -> bool: ...

    @abstractmethod
    def start(self, component: StandComponent) -> None: ...

    @abstractmethod
    def wait_ready(self, component: StandComponent) -> None: ...

    @abstractmethod
    def stop(self, component: StandComponent) -> None: ...


class StandShutdown(StandStartup, Protocol):
    @abstractmethod
    def stop_containers(self) -> None: ...


class StandDiagnostics(Protocol):
    """Read-only command output goes to the caller's streams.

    Each call is bounded and raises StandOperationError on failure.
    """

    @abstractmethod
    def show_vm_status(self) -> None: ...

    @abstractmethod
    def show_model_status(self) -> None: ...

    @abstractmethod
    def show_container_status(self) -> None: ...

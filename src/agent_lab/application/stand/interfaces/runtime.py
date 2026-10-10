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

    def exclusive(self) -> AbstractContextManager[None]:
        raise NotImplementedError

    def is_started(self, component: StandComponent) -> bool:
        raise NotImplementedError

    def start(self, component: StandComponent) -> None:
        raise NotImplementedError

    def wait_ready(self, component: StandComponent) -> None:
        raise NotImplementedError

    def stop(self, component: StandComponent) -> None:
        raise NotImplementedError


class StandShutdown(StandStartup, Protocol):
    def stop_containers(self) -> None:
        raise NotImplementedError


class StandDiagnostics(Protocol):
    """Read-only command output goes to the caller's streams.

    Each call is bounded and raises StandOperationError on failure.
    """

    def show_vm_status(self) -> None:
        raise NotImplementedError

    def show_model_status(self) -> None:
        raise NotImplementedError

    def show_container_status(self) -> None:
        raise NotImplementedError

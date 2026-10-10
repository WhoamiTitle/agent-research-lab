from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.stand.components import StandComponent
from agent_lab.application.stand.interfaces.runtime import StandDiagnostics, StandShutdown

FIXTURE_EXIT_CODE: Final = 19


class RuntimeMock(StandShutdown, StandDiagnostics):
    def __init__(
        self,
        *,
        fail_on: str | None = None,
        failures: tuple[str, ...] = (),
        interrupt_on: str | None = None,
        existing_components: frozenset[StandComponent] = frozenset(),
    ) -> None:
        self.calls: list[str] = []
        self.active_components = set(existing_components)
        self._fail_on = fail_on
        self._failures = failures
        self._interrupt_on = interrupt_on

    def _record(self, operation: str) -> None:
        self.calls.append(operation)
        if operation == self._interrupt_on:
            raise KeyboardInterrupt
        if operation == self._fail_on or operation in self._failures:
            raise StandOperationError("fixture failure", exit_code=FIXTURE_EXIT_CODE)

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        self._record("lock")
        try:
            yield
        finally:
            self._record("unlock")

    def is_started(self, component: StandComponent) -> bool:
        self._record(f"inspect-{component}")
        return component in self.active_components

    def start(self, component: StandComponent) -> None:
        self.active_components.add(component)
        self._record(f"start-{component}")

    def wait_ready(self, component: StandComponent) -> None:
        self._record(f"ready-{component}")

    def stop(self, component: StandComponent) -> None:
        self._record(f"stop-{component}")
        self.active_components.discard(component)

    def stop_containers(self) -> None:
        self._record("stop-containers")

    def show_vm_status(self) -> None:
        self._record("vm-status")

    def show_model_status(self) -> None:
        self._record("model-status")

    def show_container_status(self) -> None:
        self._record("container-status")

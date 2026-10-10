from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.stand.components import StandComponent
from agent_lab.application.stand.interfaces.runtime import StandStartup


class StartStandHandler:
    def __init__(self, startup: StandStartup) -> None:
        self._startup = startup

    def __call__(self) -> None:
        with self._startup.exclusive():
            owned_components: list[StandComponent] = []
            try:
                for component in StandComponent:
                    if not self._startup.is_started(component):
                        # Register before mutation: a timeout can leave the job loaded.
                        owned_components.append(component)
                        self._startup.start(component)
                    self._startup.wait_ready(component)
            except BaseException as error:
                # Lifecycle cleanup also applies to cancellation and unexpected errors.
                failures = self._rollback(owned_components)
                if failures:
                    if isinstance(error, (StandOperationError, KeyboardInterrupt)):
                        exit_code = error.exit_code if isinstance(error, StandOperationError) else 130
                        message = str(error) if isinstance(error, StandOperationError) else "Interrupted."
                        raise StandOperationError("\n".join((message, *failures)), exit_code=exit_code) from error
                    error.add_note("\n".join(failures))
                raise

    def _rollback(self, components: list[StandComponent]) -> tuple[str, ...]:
        failures: list[str] = []
        for component in reversed(components):
            try:
                self._startup.stop(component)
            except (StandOperationError, KeyboardInterrupt) as error:
                failures.append(f"Cleanup failed for {component}: {error or 'interrupted'}")
        return tuple(failures)

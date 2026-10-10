from agent_lab.application.stand.components import StandComponent
from agent_lab.application.stand.interfaces.runtime import StandShutdown


class StopStandHandler:
    def __init__(self, shutdown: StandShutdown) -> None:
        self._shutdown = shutdown

    def __call__(self) -> None:
        with self._shutdown.exclusive():
            for component in reversed(StandComponent):
                if component == StandComponent.VM:
                    self._shutdown.stop_containers()
                self._shutdown.stop(component)

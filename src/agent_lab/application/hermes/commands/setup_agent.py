from agent_lab.application.hermes.interfaces.runtime import HermesSetup


class SetupAgentHandler:
    def __init__(self, runtime: HermesSetup) -> None:
        self._runtime = runtime

    def __call__(self) -> None:
        self._runtime.setup()

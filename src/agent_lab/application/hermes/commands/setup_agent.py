from dataclasses import dataclass

from agent_lab.application.hermes.interfaces.runtime import HermesSetup


@dataclass(frozen=True, slots=True, kw_only=True)
class SetupAgent:
    gateway_only: bool = False


class SetupAgentHandler:
    def __init__(self, runtime: HermesSetup) -> None:
        self._runtime = runtime

    def __call__(self, command: SetupAgent) -> None:
        self._runtime.setup(gateway_only=command.gateway_only)

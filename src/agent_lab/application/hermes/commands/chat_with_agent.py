from dataclasses import dataclass

from agent_lab.application.hermes.interfaces.runtime import HermesChat


@dataclass(frozen=True, slots=True)
class ChatWithAgent:
    arguments: tuple[str, ...]


class ChatWithAgentHandler:
    def __init__(self, runtime: HermesChat) -> None:
        self._runtime = runtime

    def __call__(self, command: ChatWithAgent) -> None:
        self._runtime.chat(command.arguments)

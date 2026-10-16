import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.deployment.commands.sync_deployment import SyncDeploymentHandler
from agent_lab.application.hermes.commands.chat_with_agent import ChatWithAgent, ChatWithAgentHandler
from agent_lab.application.hermes.commands.install_web_dependencies import InstallWebDependenciesHandler
from agent_lab.application.hermes.commands.setup_agent import SetupAgent, SetupAgentHandler
from agent_lab.application.hermes.commands.start_gateway import StartGatewayHandler
from agent_lab.application.model.commands.prepare_model import PrepareModelHandler
from agent_lab.application.stand.commands.start_stand import StartStandHandler
from agent_lab.application.stand.commands.stop_stand import StopStandHandler
from agent_lab.application.stand.queries.get_stand_status import GetStandStatusHandler


class Command(StrEnum):
    START = "start"
    STOP = "stop"
    MODEL = "model"
    SYNC = "sync"
    SETUP = "setup"
    WEB_DEPS = "web-deps"
    CHAT = "chat"
    GATEWAY = "gateway"
    STATUS = "status"


USAGE: Final = "Usage: scripts/lab.sh start|stop|model|sync|setup|web-deps|chat|gateway|status"


@dataclass(frozen=True, slots=True, kw_only=True)
class CliHandlers:
    start_stand: StartStandHandler
    stop_stand: StopStandHandler
    get_stand_status: GetStandStatusHandler
    prepare_model: PrepareModelHandler
    sync_deployment: SyncDeploymentHandler
    setup_agent: SetupAgentHandler
    install_web_dependencies: InstallWebDependenciesHandler
    chat_with_agent: ChatWithAgentHandler
    start_gateway: StartGatewayHandler


class LabCli:
    def __init__(self, handlers: CliHandlers) -> None:
        self._handlers = handlers

    def run(self, arguments: Sequence[str]) -> int:
        if not arguments or arguments[0] not in Command:
            print(USAGE)
            return 0
        command = Command(arguments[0])
        if command in {Command.START, Command.STOP, Command.STATUS}:
            parser = argparse.ArgumentParser(prog="agent-lab")
            parser.add_argument("command", choices=(Command.START, Command.STOP, Command.STATUS))
            parser.parse_args(arguments)
        try:
            self._dispatch(command, tuple(arguments[1:]))
        except StandOperationError as error:
            print(error, file=sys.stderr)
            return error.exit_code
        except KeyboardInterrupt:
            print("Interrupted.", file=sys.stderr)
            return 130
        return 0

    def _dispatch(self, command: Command, arguments: tuple[str, ...]) -> None:
        match command:
            case Command.START:
                self._handlers.start_stand()
                print("VM and the selected local Ollama backend are ready.")
            case Command.STOP:
                self._handlers.stop_stand()
            case Command.STATUS:
                self._handlers.get_stand_status()
            case Command.MODEL:
                self._handlers.prepare_model()
            case Command.SYNC:
                self._handlers.sync_deployment()
            case Command.SETUP:
                self._handlers.setup_agent(SetupAgent(gateway_only="--gateway-only" in arguments))
            case Command.WEB_DEPS:
                self._handlers.install_web_dependencies()
            case Command.CHAT:
                self._handlers.chat_with_agent(ChatWithAgent(arguments=arguments))
            case Command.GATEWAY:
                self._handlers.start_gateway()

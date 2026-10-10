import argparse
import sys
from collections.abc import Sequence
from enum import StrEnum

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.stand.commands.start_stand import StartStandHandler
from agent_lab.application.stand.commands.stop_stand import StopStandHandler
from agent_lab.application.stand.queries.get_stand_status import GetStandStatusHandler


class Command(StrEnum):
    START = "start"
    STOP = "stop"
    STATUS = "status"


class CliArguments(argparse.Namespace):
    command: str


class LabCli:
    def __init__(
        self, start_stand: StartStandHandler, stop_stand: StopStandHandler, get_stand_status: GetStandStatusHandler
    ) -> None:
        self._start_stand = start_stand
        self._stop_stand = stop_stand
        self._get_stand_status = get_stand_status

    def run(self, arguments: Sequence[str]) -> int:
        parser = argparse.ArgumentParser(prog="agent-lab")
        parser.add_argument("command", choices=tuple(Command))
        parsed = CliArguments()
        parser.parse_args(arguments, namespace=parsed)
        try:
            match Command(parsed.command):
                case Command.START:
                    self._start_stand()
                    print("VM, local Ollama and the tunnel are ready.")
                case Command.STOP:
                    self._stop_stand()
                case Command.STATUS:
                    self._get_stand_status()
        except StandOperationError as error:
            print(error, file=sys.stderr)
            return error.exit_code
        except KeyboardInterrupt:
            print("Interrupted.", file=sys.stderr)
            return 130
        return 0

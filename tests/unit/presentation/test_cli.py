import pytest

from agent_lab.application.stand.commands.start_stand import StartStandHandler
from agent_lab.application.stand.commands.stop_stand import StopStandHandler
from agent_lab.application.stand.queries.get_stand_status import GetStandStatusHandler
from agent_lab.presentation.cli.main import LabCli
from tests.mocks.runtime import FIXTURE_EXIT_CODE, RuntimeMock


def test_cli_returns_application_error_without_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    runtime = RuntimeMock(fail_on="start-vm")
    cli = LabCli(StartStandHandler(runtime), StopStandHandler(runtime), GetStandStatusHandler(runtime))

    exit_code = cli.run(["start"])

    assert exit_code == FIXTURE_EXIT_CODE
    assert capsys.readouterr().err == "fixture failure\n"

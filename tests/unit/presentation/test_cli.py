import pytest

from tests.fixtures.cli import build_cli
from tests.mocks.preparation import PreparationMock
from tests.mocks.runtime import FIXTURE_EXIT_CODE, RuntimeMock


def test_cli_returns_application_error_without_traceback(capsys: pytest.CaptureFixture[str]) -> None:
    runtime = RuntimeMock(fail_on="start-vm")
    cli = build_cli(runtime, PreparationMock())

    exit_code = cli.run(["start"])

    assert exit_code == FIXTURE_EXIT_CODE
    assert capsys.readouterr().err == "fixture failure\n"

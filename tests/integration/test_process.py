import sys
from pathlib import Path
from typing import Final

import pytest

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.infrastructure.process import ProcessRunner

FAILURE_EXIT_CODE: Final = 7
NOT_FOUND_EXIT_CODE: Final = 127
TIMEOUT_EXIT_CODE: Final = 124
SIGTERM_EXIT_CODE: Final = 143


def test_child_exit_code_is_preserved() -> None:
    with pytest.raises(StandOperationError) as caught:
        ProcessRunner().run((sys.executable, "-c", f"raise SystemExit({FAILURE_EXIT_CODE})"), timeout=5)
    assert caught.value.exit_code == FAILURE_EXIT_CODE


def test_missing_executable_has_cli_error_code(tmp_path: Path) -> None:
    executable = str(tmp_path / "absent")
    with pytest.raises(StandOperationError) as caught:
        ProcessRunner().run((executable,), timeout=5)
    assert caught.value.exit_code == NOT_FOUND_EXIT_CODE


def test_timeout_bounds_wait_for_child() -> None:
    with pytest.raises(StandOperationError) as caught:
        ProcessRunner().run((sys.executable, "-c", "import time; time.sleep(10)"), timeout=0.1)
    assert caught.value.exit_code == TIMEOUT_EXIT_CODE


def test_child_signal_uses_shell_exit_code() -> None:
    with pytest.raises(StandOperationError) as caught:
        ProcessRunner().run(
            (sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"),
            timeout=5,
        )
    assert caught.value.exit_code == SIGTERM_EXIT_CODE

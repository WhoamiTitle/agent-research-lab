import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Final

import pytest

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.infrastructure.process import ProcessRunner

TIMEOUT_EXIT_CODE: Final = 124
INTERRUPT_EXIT_CODE: Final = 130


def wait_until_gone(pid: int) -> bool:
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.01)
    return False


def test_timeout_kills_foreground_descendants_and_reaps_parent(tmp_path: Path) -> None:
    pid_file = tmp_path / "pids"
    source = (
        "import os, subprocess, sys, time; from pathlib import Path; "
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)']); "
        "Path(sys.argv[1]).write_text(f'{os.getpid()} {child.pid}'); time.sleep(10)"
    )

    with pytest.raises(StandOperationError) as error:
        ProcessRunner().capture((sys.executable, "-c", source, str(pid_file)), timeout=0.3)

    assert error.value.exit_code == TIMEOUT_EXIT_CODE
    assert all(wait_until_gone(int(pid)) for pid in pid_file.read_text().split())


def test_interrupt_reaps_command_before_returning_to_caller(tmp_path: Path) -> None:
    pid_file = tmp_path / "pid"
    project_source = Path(__file__).resolve().parents[2] / "src"
    runner_source = """import sys
sys.path.insert(0, sys.argv[1])
from agent_lab.infrastructure.process import ProcessRunner
try:
    ProcessRunner().run((sys.executable, "-c",
        "import os, sys, time; from pathlib import Path; "
        "Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(10)", sys.argv[2]), timeout=15)
except KeyboardInterrupt:
    raise SystemExit(130)
"""
    with subprocess.Popen(
        (sys.executable, "-c", runner_source, str(project_source), str(pid_file)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as runner:
        deadline = time.monotonic() + 3
        while not pid_file.is_file() and time.monotonic() < deadline:
            time.sleep(0.01)
        try:
            assert pid_file.is_file()
            os.kill(runner.pid, signal.SIGINT)
            stdout, stderr = runner.communicate(timeout=3)
        finally:
            if runner.poll() is None:
                runner.kill()
                runner.wait(timeout=1)

    assert runner.returncode == INTERRUPT_EXIT_CODE, (stdout, stderr)
    assert wait_until_gone(int(pid_file.read_text()))

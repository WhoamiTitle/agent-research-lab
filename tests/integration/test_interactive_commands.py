from pathlib import Path
from typing import Final

import pytest

from tests.fixtures.lab import LabShell
from tests.fixtures.terminal import open_terminal

INTERRUPT_EXIT_CODE: Final = 130
TIMEOUT_EXIT_CODE: Final = 124


def wrapper_terminal_script(lab_shell: LabShell, command: str) -> Path:
    script = lab_shell.directory / "terminal-wrapper.py"
    arguments = (str(lab_shell.project / "scripts/lab.sh"), command)
    script.write_text(
        f"import fcntl, os, termios\nfcntl.ioctl(0, termios.TIOCSCTTY, 0)\nos.execv({arguments[0]!r}, {arguments!r})\n",
        encoding="utf-8",
    )
    return script


@pytest.mark.parametrize("command", ["setup", "chat"])
def test_interactive_command_keeps_controlling_terminal_and_input(lab_shell: LabShell, command: str) -> None:
    lab_shell.environment["LAB_TEST_TERMINAL"] = "1"

    with open_terminal(wrapper_terminal_script(lab_shell, command), lab_shell.environment) as session:
        session.read_until(b"READY_TTY=True")
        session.write(b"two words\n")
        session.read_until(b"ANSWER=two words")
        assert session.process.wait(timeout=3) == 0


def test_chat_ctrl_c_returns_shell_code_without_traceback(lab_shell: LabShell) -> None:
    lab_shell.environment["LAB_TEST_TERMINAL"] = "1"

    with open_terminal(wrapper_terminal_script(lab_shell, "chat"), lab_shell.environment) as session:
        session.read_until(b"READY_TTY=True")
        session.write(b"\x03")
        output = session.read_until(b"command exited with status 130")
        assert session.process.wait(timeout=3) == INTERRUPT_EXIT_CODE
        assert b"Traceback" not in output


def test_interactive_timeout_restores_terminal_foreground_group(tmp_path: Path) -> None:
    script = tmp_path / "terminal-timeout.py"
    source = Path(__file__).resolve().parents[2] / "src"
    script.write_text(
        "import fcntl, os, sys, termios\n"
        "fcntl.ioctl(0, termios.TIOCSCTTY, 0)\n"
        f"sys.path.insert(0, {str(source)!r})\n"
        "from agent_lab.infrastructure.process import ProcessRunner\n"
        "from agent_lab.application.common.exceptions import StandOperationError\n"
        "original_group = os.tcgetpgrp(0)\n"
        "try:\n"
        "    ProcessRunner().interactive((sys.executable, '-c', 'import time; time.sleep(10)'), timeout=0.2)\n"
        "except StandOperationError as error:\n"
        "    print('RESTORED=' + str(os.tcgetpgrp(0) == original_group), flush=True)\n"
        "    raise SystemExit(error.exit_code)\n",
        encoding="utf-8",
    )

    with open_terminal(script) as session:
        session.read_until(b"RESTORED=True")
        assert session.process.wait(timeout=3) == TIMEOUT_EXIT_CODE

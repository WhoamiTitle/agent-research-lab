import os
import signal
import subprocess
from contextlib import nullcontext, suppress
from dataclasses import dataclass
from typing import BinaryIO

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.infrastructure.terminal import foreground_terminal


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessInvocation:
    arguments: tuple[str, ...]
    timeout: float
    capture_output: bool = False
    check: bool = True
    source: BinaryIO | None = None
    interactive: bool = False


class ProcessRunner:
    """Run a foreground command with inherited streams and a finite timeout.

    Timeout or interruption kills the command's process group and reaps the
    direct child before rollback. External daemons remain the runtime's responsibility.
    """

    def run(self, arguments: tuple[str, ...], *, timeout: float) -> None:
        self._execute(ProcessInvocation(arguments=arguments, timeout=timeout))

    def capture(self, arguments: tuple[str, ...], *, timeout: float, check: bool = True) -> ProcessResult:
        return self._execute(ProcessInvocation(arguments=arguments, timeout=timeout, capture_output=True, check=check))

    def run_with_input(self, arguments: tuple[str, ...], *, source: BinaryIO, timeout: float) -> None:
        """Borrow a binary stream for stdin; the caller retains ownership."""
        self._execute(ProcessInvocation(arguments=arguments, timeout=timeout, source=source))

    def interactive(self, arguments: tuple[str, ...], *, timeout: float) -> None:
        self._execute(ProcessInvocation(arguments=arguments, timeout=timeout, interactive=True))

    def _execute(self, invocation: ProcessInvocation) -> ProcessResult:
        arguments, timeout = invocation.arguments, invocation.timeout
        try:
            with subprocess.Popen(
                arguments,
                text=True,
                start_new_session=not invocation.interactive,
                process_group=0 if invocation.interactive else None,
                stdin=invocation.source,
                stdout=subprocess.PIPE if invocation.capture_output else None,
                stderr=subprocess.PIPE if invocation.capture_output else None,
            ) as process:
                try:
                    with foreground_terminal(process.pid) if invocation.interactive else nullcontext():
                        stdout, stderr = process.communicate(timeout=timeout)
                except BaseException:
                    self._terminate(process)
                    raise
                returncode = process.wait(timeout=1.0)
        except subprocess.TimeoutExpired as error:
            raise StandOperationError(
                f"{arguments[0]}: timeout after {timeout:g}s.",
                exit_code=124,
            ) from error
        except FileNotFoundError as error:
            raise StandOperationError(
                f"{arguments[0]}: executable not found.",
                exit_code=127,
            ) from error
        except OSError as error:
            raise StandOperationError(
                f"{arguments[0]}: {error.strerror}.",
                exit_code=126,
            ) from error
        if invocation.check and returncode != 0:
            exit_code = returncode if returncode >= 0 else 128 - returncode
            raise StandOperationError(f"{arguments[0]}: command exited with status {exit_code}.", exit_code=exit_code)
        return ProcessResult(returncode=returncode, stdout=stdout or "", stderr=stderr or "")

    @staticmethod
    def _terminate(process: subprocess.Popen[str]) -> None:
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
        process.wait(timeout=1.0)

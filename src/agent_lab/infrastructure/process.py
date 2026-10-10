import os
import signal
import subprocess
from contextlib import suppress
from dataclasses import dataclass

from agent_lab.application.common.exceptions import StandOperationError


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


class ProcessRunner:
    """Run a foreground command with inherited streams and a finite timeout.

    Timeout or interruption kills the command's process group and reaps the
    direct child before rollback. External daemons remain the runtime's responsibility.
    """

    def run(self, arguments: tuple[str, ...], *, timeout: float) -> None:
        self._execute(arguments, timeout=timeout, capture_output=False, check=True)

    def capture(self, arguments: tuple[str, ...], *, timeout: float, check: bool = True) -> ProcessResult:
        return self._execute(arguments, timeout=timeout, capture_output=True, check=check)

    def _execute(
        self, arguments: tuple[str, ...], *, timeout: float, capture_output: bool, check: bool
    ) -> ProcessResult:
        try:
            with subprocess.Popen(
                arguments,
                text=True,
                start_new_session=True,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
            ) as process:
                try:
                    stdout, stderr = process.communicate(timeout=timeout)
                except (subprocess.TimeoutExpired, KeyboardInterrupt):
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
        if check and returncode != 0:
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

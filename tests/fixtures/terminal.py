import errno
import os
import pty
import select
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class TerminalSession:
    process: subprocess.Popen[bytes]
    descriptor: int

    def read_until(self, expected: bytes, *, timeout: float = 5.0) -> bytes:
        output = bytearray()
        deadline = time.monotonic() + timeout
        while expected not in output and (remaining := deadline - time.monotonic()) > 0:
            readable, _, _ = select.select([self.descriptor], [], [], remaining)
            if not readable:
                break
            try:
                part = os.read(self.descriptor, 4096)
            except OSError as error:
                if error.errno == errno.EIO:
                    break
                raise
            if not part:
                break
            output.extend(part)
        assert expected in output, bytes(output)
        return bytes(output)

    def write(self, data: bytes) -> None:
        os.write(self.descriptor, data)


@contextmanager
def open_terminal(script: Path, environment: dict[str, str] | None = None) -> Iterator[TerminalSession]:
    master_descriptor, slave_descriptor = pty.openpty()
    with (
        os.fdopen(master_descriptor, "rb", buffering=0) as master,
        os.fdopen(slave_descriptor, "rb", buffering=0) as slave,
        subprocess.Popen(
            (sys.executable, str(script)),
            stdin=slave,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
            env=environment,
        ) as process,
    ):
        slave.close()
        try:
            yield TerminalSession(process=process, descriptor=master.fileno())
        finally:
            master.close()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)

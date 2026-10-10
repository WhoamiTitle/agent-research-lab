import fcntl
import time
from collections.abc import Iterator
from contextlib import contextmanager

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.infrastructure.runtime.config import RuntimeConfig


class LifecycleLockImpl:
    def __init__(self, config: RuntimeConfig) -> None:
        self._config = config

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        directory = self._config.runtime_directory
        try:
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            with (directory / "lifecycle.lock").open("a", encoding="utf-8") as lock_file:
                (directory / "lifecycle.lock").chmod(0o600)
                deadline = time.monotonic() + self._config.lock_timeout
                while True:
                    try:
                        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError as error:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise StandOperationError(
                                "Another lab lifecycle command holds the lock.", exit_code=124
                            ) from error
                        time.sleep(min(self._config.poll_interval, remaining))
                try:
                    yield
                finally:
                    # Keep the file: unlinking it would let another caller lock a new inode.
                    fcntl.flock(lock_file, fcntl.LOCK_UN)
        except OSError as error:
            raise StandOperationError(f"Cannot use the lab lifecycle lock: {error.strerror}.") from error

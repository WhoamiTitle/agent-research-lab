import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class BotAlreadyRunningError(Exception):
    pass


@contextmanager
def single_process(directory: Path) -> Iterator[None]:
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / "polling.lock").open("a", encoding="utf-8") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise BotAlreadyRunningError("A bot worker already owns this data directory.") from None
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

import os
import signal
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from typing import Final

STDIN_FILENO: Final = 0


def assign_foreground(process_group: int) -> None:
    previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGTTOU})
    try:
        os.tcsetpgrp(STDIN_FILENO, process_group)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)


@contextmanager
def foreground_terminal(process_group: int) -> Iterator[None]:
    """Lend the controlling terminal to an owned child group, then restore it."""
    original_group: int | None = None
    if os.isatty(STDIN_FILENO):
        with suppress(OSError):
            original_group = os.tcgetpgrp(STDIN_FILENO)
    if original_group is None or original_group != os.getpgrp():
        yield
        return
    try:
        assign_foreground(process_group)
        # A child that read before the hand-off may have received SIGTTIN.
        with suppress(ProcessLookupError):
            os.killpg(process_group, signal.SIGCONT)
        yield
    finally:
        assign_foreground(original_group)

from pathlib import Path
from typing import Final

import pytest

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.infrastructure.runtime.config import RuntimeConfig
from agent_lab.infrastructure.runtime.lock import LifecycleLockImpl

TIMEOUT_EXIT_CODE: Final = 124


def test_lock_times_out_without_effects_then_can_be_reused(tmp_path: Path) -> None:
    config = RuntimeConfig(project_root=tmp_path, home_directory=tmp_path, lock_timeout=0.03, poll_interval=0.005)
    first = LifecycleLockImpl(config)
    second = LifecycleLockImpl(config)

    with first.exclusive(), pytest.raises(StandOperationError, match="holds the lock") as error, second.exclusive():
        pytest.fail("The second lock must not be acquired.")

    assert error.value.exit_code == TIMEOUT_EXIT_CODE
    with second.exclusive():
        assert (config.runtime_directory / "lifecycle.lock").is_file()


def test_unexpected_failure_releases_lock(tmp_path: Path) -> None:
    config = RuntimeConfig(project_root=tmp_path, home_directory=tmp_path)
    lock = LifecycleLockImpl(config)

    with pytest.raises(RuntimeError, match="fixture"), lock.exclusive():
        raise RuntimeError("fixture")

    with lock.exclusive():
        assert (config.runtime_directory / "lifecycle.lock").is_file()

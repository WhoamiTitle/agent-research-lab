from pathlib import Path
from typing import Final

import pytest

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.stand.components import StandComponent
from agent_lab.infrastructure.runtime.config import OllamaBackend, RuntimeConfig
from agent_lab.infrastructure.runtime.launchd import LaunchdServicesImpl
from agent_lab.infrastructure.runtime.lock import LifecycleLockImpl
from agent_lab.infrastructure.runtime.main import LocalRuntimeImpl
from tests.mocks.process import ReadinessRunnerMock

TIMEOUT_EXIT_CODE: Final = 124


@pytest.mark.parametrize("response", ["null", "[]", "{}", '{"version": 42}', '{"version": " "}', "invalid JSON"])
@pytest.mark.parametrize("backend", list(OllamaBackend))
def test_http_success_with_invalid_payload_is_not_ready(tmp_path: Path, response: str, backend: OllamaBackend) -> None:
    config = RuntimeConfig(
        project_root=tmp_path,
        home_directory=tmp_path,
        ollama_backend=backend,
        readiness_timeout=0.02,
        poll_interval=0.001,
    )
    runner = ReadinessRunnerMock(response=response)
    runtime = LocalRuntimeImpl(config, runner, LaunchdServicesImpl(config, runner), LifecycleLockImpl(config))

    with pytest.raises(StandOperationError, match="did not become ready") as error:
        runtime.wait_ready(StandComponent.OLLAMA)

    assert error.value.exit_code == TIMEOUT_EXIT_CODE


def test_loaded_job_without_pid_does_not_accept_another_process_api(tmp_path: Path) -> None:
    config = RuntimeConfig(project_root=tmp_path, home_directory=tmp_path, readiness_timeout=0.02, poll_interval=0.001)
    runner = ReadinessRunnerMock(response='{"version": "fixture"}', pid=None)
    runtime = LocalRuntimeImpl(config, runner, LaunchdServicesImpl(config, runner), LifecycleLockImpl(config))

    with pytest.raises(StandOperationError, match="did not become ready"):
        runtime.wait_ready(StandComponent.OLLAMA)

    assert not any(arguments[0] == "curl" for arguments, _, _ in runner.calls)

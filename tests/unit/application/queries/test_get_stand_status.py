import pytest

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.stand.queries.get_stand_status import GetStandStatusHandler
from tests.mocks.runtime import RuntimeMock


def test_status_visits_vm_model_and_containers() -> None:
    runtime = RuntimeMock()
    handler = GetStandStatusHandler(runtime)

    handler()

    assert runtime.calls == ["vm-status", "model-status", "container-status"]


def test_model_failure_prevents_container_probe() -> None:
    runtime = RuntimeMock(fail_on="model-status")
    handler = GetStandStatusHandler(runtime)

    with pytest.raises(StandOperationError, match="fixture failure"):
        handler()

    assert runtime.calls == ["vm-status", "model-status"]

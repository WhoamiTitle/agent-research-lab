import pytest

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.stand.commands.start_stand import StartStandHandler
from agent_lab.application.stand.components import StandComponent
from tests.mocks.runtime import FIXTURE_EXIT_CODE, RuntimeMock


def test_vm_precedes_services_and_success_keeps_resources() -> None:
    runtime = RuntimeMock()

    StartStandHandler(runtime)()

    assert runtime.active_components == set(StandComponent)
    assert [call for call in runtime.calls if call.startswith("start-")] == [
        "start-vm",
        "start-ollama",
        "start-ollama-tunnel",
    ]
    assert runtime.calls[0] == "lock"
    assert runtime.calls[-1] == "unlock"


def test_repeated_start_only_checks_existing_resources() -> None:
    runtime = RuntimeMock(existing_components=frozenset(StandComponent))

    StartStandHandler(runtime)()
    StartStandHandler(runtime)()

    assert runtime.active_components == set(StandComponent)
    assert not any(call.startswith(("start-", "stop-")) for call in runtime.calls)


@pytest.mark.parametrize(
    "failed_operation",
    ["start-vm", "ready-vm", "start-ollama", "ready-ollama", "start-ollama-tunnel", "ready-ollama-tunnel"],
)
def test_partial_creation_failure_releases_all_owned_resources(failed_operation: str) -> None:
    runtime = RuntimeMock(fail_on=failed_operation)

    with pytest.raises(StandOperationError, match="fixture failure") as failure:
        StartStandHandler(runtime)()

    assert failure.value.exit_code == FIXTURE_EXIT_CODE
    assert runtime.active_components == set()
    assert runtime.calls[-1] == "unlock"
    stops = [call for call in runtime.calls if call.startswith("stop-")]
    assert stops == list(
        reversed([call.replace("start-", "stop-") for call in runtime.calls if call.startswith("start-")])
    )


@pytest.mark.parametrize(
    "existing", [frozenset({StandComponent.VM}), frozenset({StandComponent.VM, StandComponent.OLLAMA})]
)
def test_failure_preserves_resources_that_existed_before_start(existing: frozenset[StandComponent]) -> None:
    runtime = RuntimeMock(existing_components=existing, fail_on="start-ollama-tunnel")

    with pytest.raises(StandOperationError, match="fixture failure"):
        StartStandHandler(runtime)()

    assert runtime.active_components == existing
    assert not any(f"stop-{component}" in runtime.calls for component in existing)


def test_existing_unhealthy_service_is_preserved_without_restart() -> None:
    runtime = RuntimeMock(existing_components=frozenset(StandComponent), fail_on="ready-ollama")

    with pytest.raises(StandOperationError, match="fixture failure"):
        StartStandHandler(runtime)()

    assert runtime.active_components == set(StandComponent)
    assert not any(call.startswith(("start-", "stop-")) for call in runtime.calls)


def test_rollback_continues_after_cleanup_failure_and_preserves_original_exit_code() -> None:
    runtime = RuntimeMock(fail_on="ready-ollama-tunnel", failures=("stop-ollama-tunnel", "stop-ollama"))

    with pytest.raises(StandOperationError, match="Cleanup failed for ollama-tunnel") as failure:
        StartStandHandler(runtime)()

    assert failure.value.exit_code == FIXTURE_EXIT_CODE
    assert "Cleanup failed for ollama:" in str(failure.value)
    assert StandComponent.VM not in runtime.active_components
    assert runtime.calls[-2:] == ["stop-vm", "unlock"]


def test_interruption_rolls_back_before_propagating() -> None:
    runtime = RuntimeMock(interrupt_on="ready-ollama")

    with pytest.raises(KeyboardInterrupt):
        StartStandHandler(runtime)()

    assert runtime.active_components == set()
    assert runtime.calls[-3:] == ["stop-ollama", "stop-vm", "unlock"]


def test_inspection_failure_does_not_claim_existing_resource() -> None:
    runtime = RuntimeMock(existing_components=frozenset(StandComponent), fail_on="inspect-vm")

    with pytest.raises(StandOperationError, match="fixture failure"):
        StartStandHandler(runtime)()

    assert runtime.active_components == set(StandComponent)
    assert runtime.calls == ["lock", "inspect-vm", "unlock"]

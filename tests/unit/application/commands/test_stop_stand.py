from agent_lab.application.stand.commands.stop_stand import StopStandHandler
from agent_lab.application.stand.components import StandComponent
from tests.mocks.runtime import RuntimeMock


def test_explicit_stop_uses_the_same_lock_and_preserves_shutdown_order() -> None:
    runtime = RuntimeMock(existing_components=frozenset(StandComponent))

    StopStandHandler(runtime)()

    assert runtime.active_components == set()
    assert runtime.calls == ["lock", "stop-ollama-tunnel", "stop-ollama", "stop-containers", "stop-vm", "unlock"]

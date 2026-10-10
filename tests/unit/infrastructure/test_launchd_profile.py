import plistlib
from pathlib import Path
from typing import cast

from agent_lab.application.stand.components import StandComponent
from agent_lab.infrastructure.process import ProcessRunner
from agent_lab.infrastructure.runtime.config import RuntimeConfig
from agent_lab.infrastructure.runtime.launchd import LaunchAgent, LaunchdServicesImpl
from tests.mocks.process import ReadinessRunnerMock


def test_tunnel_uses_its_own_connection_despite_lima_multiplexing(tmp_path: Path) -> None:
    config = RuntimeConfig(project_root=tmp_path, home_directory=tmp_path)
    ssh_config = tmp_path / ".lima/agent-research/ssh.config"
    ssh_config.parent.mkdir(parents=True)
    ssh_config.write_text(
        f"Host lima-agent-research\n  HostName 127.0.0.1\n  ControlMaster auto\n"
        f"  ControlPath {tmp_path / 'shared.sock'}\n  ControlPersist yes\n",
    )
    services = LaunchdServicesImpl(config, ReadinessRunnerMock(response=""))
    services.start(StandComponent.TUNNEL)
    agent = cast("LaunchAgent", plistlib.loads((config.runtime_directory / "ollama-tunnel.plist").read_bytes()))

    effective = ProcessRunner().capture((agent["ProgramArguments"][0], "-G", *agent["ProgramArguments"][1:]), timeout=3)

    settings = [line for line in effective.stdout.splitlines() if line.startswith("control")]
    assert settings == ["controlmaster false", "controlpersist no"]

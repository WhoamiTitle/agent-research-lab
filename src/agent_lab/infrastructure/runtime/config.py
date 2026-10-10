from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeConfig:
    project_root: Path
    home_directory: Path
    vm_name: str = "agent-research"
    compose_path: str = "/srv/agent-lab/deployment/infra/hermes/compose.yaml"
    vm_start_timeout: float = 600.0
    status_timeout: float = 30.0
    service_timeout: float = 10.0
    readiness_timeout: float = 30.0
    probe_timeout: float = 3.0
    poll_interval: float = 0.25
    lock_timeout: float = 60.0
    vm_stop_timeout: float = 60.0

    @property
    def runtime_directory(self) -> Path:
        return self.home_directory / ".local/share/agent-research-lab"

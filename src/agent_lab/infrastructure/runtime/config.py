from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PurePosixPath


class OllamaBackend(StrEnum):
    MAC = "mac"
    DOCKER = "docker"


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeConfig:
    project_root: Path
    home_directory: Path
    ollama_backend: OllamaBackend = OllamaBackend.MAC
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
    model_pull_timeout: float = 1800.0
    model_create_timeout: float = 300.0
    sync_timeout: float = 120.0
    web_install_timeout: float = 900.0
    gateway_timeout: float = 120.0
    image_build_timeout: float = 900.0
    interactive_timeout: float = 86400.0

    @property
    def runtime_directory(self) -> Path:
        return self.home_directory / ".local/share/agent-research-lab"

    @property
    def deployment_directory(self) -> PurePosixPath:
        return PurePosixPath(self.compose_path).parents[2]

import json
import time
from contextlib import AbstractContextManager

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.stand.components import StandComponent
from agent_lab.application.stand.interfaces.runtime import StandDiagnostics, StandShutdown
from agent_lab.infrastructure.process import ProcessResult, ProcessRunner
from agent_lab.infrastructure.runtime.commands import compose_arguments, guest_arguments
from agent_lab.infrastructure.runtime.config import RuntimeConfig
from agent_lab.infrastructure.runtime.launchd import LaunchdServicesImpl
from agent_lab.infrastructure.runtime.lock import LifecycleLockImpl

type JsonValue = str | int | float | bool | list[JsonValue] | dict[str, JsonValue] | None


def is_version_response(output: str) -> bool:
    try:
        response: JsonValue = json.loads(output)
    except json.JSONDecodeError:
        return False
    return (
        isinstance(response, dict)
        and "version" in response
        and isinstance(response["version"], str)
        and bool(response["version"].strip())
    )


class LocalRuntimeImpl(StandShutdown, StandDiagnostics):
    def __init__(
        self, config: RuntimeConfig, runner: ProcessRunner, services: LaunchdServicesImpl, lock: LifecycleLockImpl
    ) -> None:
        self._config = config
        self._runner = runner
        self._services = services
        self._lock = lock

    def exclusive(self) -> AbstractContextManager[None]:
        return self._lock.exclusive()

    def is_started(self, component: StandComponent) -> bool:
        if component != StandComponent.VM:
            return self._services.inspect(component).loaded
        status = self._vm_status()
        if status == "Running":
            return True
        if status in {"", "Stopped"}:
            return False
        raise StandOperationError(f"VM {self._config.vm_name} cannot be started while its status is {status}.")

    def start(self, component: StandComponent) -> None:
        if component == StandComponent.VM:
            self._start_vm()
        else:
            if component == StandComponent.OLLAMA and self._probe_api(in_vm=False).returncode == 0:
                raise StandOperationError("Port 11434 already serves HTTP outside the lab's Ollama service.")
            self._services.start(component)

    def wait_ready(self, component: StandComponent) -> None:
        if component == StandComponent.VM:
            self._runner.capture(guest_arguments(self._config, "true"), timeout=self._config.status_timeout)
        else:
            self._wait_service(component)

    def stop(self, component: StandComponent) -> None:
        if component == StandComponent.VM:
            if self._vm_status() not in {"", "Stopped"}:
                self._runner.run(("limactl", "stop", self._config.vm_name), timeout=self._config.vm_stop_timeout)
        else:
            self._services.stop(component)

    def stop_containers(self) -> None:
        if self._vm_status() == "Running":
            self._runner.run(compose_arguments(self._config, "down"), timeout=self._config.vm_stop_timeout)

    def _vm_status(self) -> str:
        return self._runner.capture(
            ("limactl", "list", "--format", "{{.Status}}", self._config.vm_name),
            timeout=self._config.status_timeout,
        ).stdout.strip()

    def _start_vm(self) -> None:
        vm_directory = self._config.home_directory / ".lima" / self._config.vm_name
        arguments: tuple[str, ...]
        if vm_directory.is_dir():
            arguments = ("limactl", "start", "--tty=false", self._config.vm_name)
        else:
            arguments = (
                "limactl",
                "start",
                "--tty=false",
                f"--name={self._config.vm_name}",
                str(self._config.project_root / "infra/lima/agent-lab.yaml"),
            )
        self._runner.run(arguments, timeout=self._config.vm_start_timeout)

    def _wait_service(self, component: StandComponent) -> None:
        deadline = time.monotonic() + self._config.readiness_timeout
        while (remaining := deadline - time.monotonic()) > 0:
            snapshot = self._services.inspect(component, timeout=min(self._config.probe_timeout, remaining))
            if snapshot.pid is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                result = self._probe_api(in_vm=component == StandComponent.TUNNEL, timeout=remaining)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                after_probe = self._services.inspect(component, timeout=min(self._config.probe_timeout, remaining))
                if result.returncode == 0 and is_version_response(result.stdout) and after_probe.pid == snapshot.pid:
                    return
            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(self._config.poll_interval, remaining))
        raise StandOperationError(
            f"{component} did not become ready within {self._config.readiness_timeout:g}s. "
            f"Check {self._config.runtime_directory / 'logs'}.",
            exit_code=124,
        )

    def _probe_api(self, *, in_vm: bool, timeout: float | None = None) -> ProcessResult:
        budget = self._config.probe_timeout if timeout is None else min(timeout, self._config.probe_timeout)
        arguments: tuple[str, ...] = (
            "curl",
            "--fail",
            "--silent",
            "--show-error",
            "--max-time",
            f"{budget:g}",
            "http://127.0.0.1:11434/api/version",
        )
        if in_vm:
            arguments = guest_arguments(self._config, *arguments)
        return self._runner.capture(arguments, timeout=budget, check=False)

    def show_vm_status(self) -> None:
        self._runner.run(
            ("limactl", "list", self._config.vm_name),
            timeout=self._config.status_timeout,
        )

    def show_model_status(self) -> None:
        self._runner.run(("ollama", "ps"), timeout=self._config.status_timeout)

    def show_container_status(self) -> None:
        self._runner.run(compose_arguments(self._config, "ps", "--all"), timeout=self._config.status_timeout)

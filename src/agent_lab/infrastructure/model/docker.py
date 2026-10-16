import time

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.infrastructure.deployment.main import DeploymentPreparationImpl
from agent_lab.infrastructure.model.response import is_version_response
from agent_lab.infrastructure.process import ProcessRunner
from agent_lab.infrastructure.runtime.commands import compose_arguments, guest_arguments
from agent_lab.infrastructure.runtime.config import RuntimeConfig


class DockerOllamaImpl:
    def __init__(self, config: RuntimeConfig, runner: ProcessRunner) -> None:
        self._config = config
        self._runner = runner

    def is_started(self, *, timeout: float | None = None) -> bool:
        return self._inspect(timeout=timeout) is True

    def _inspect(self, *, timeout: float | None = None) -> bool | None:
        result = self._runner.capture(
            guest_arguments(
                self._config,
                "sudo",
                "docker",
                "inspect",
                "--format",
                '{{.State.Running}} {{index .Config.Labels "com.docker.compose.project"}}',
                "agent-research-ollama",
            ),
            timeout=self._config.status_timeout if timeout is None else timeout,
            check=False,
        )
        if result.returncode == 1 and "no such object" in result.stderr.lower():
            return None
        if result.returncode != 0 or result.stdout.strip() not in {
            "true agent-research-lab",
            "false agent-research-lab",
        }:
            raise StandOperationError("Cannot inspect the lab's Docker Ollama; check Docker and container ownership.")
        return result.stdout.strip().startswith("true ")

    def start(self) -> None:
        memory = self._runner.capture(
            guest_arguments(
                self._config,
                "python3",
                "-c",
                "import os; print(os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE'))",
            ),
            timeout=self._config.status_timeout,
        )
        if not memory.stdout.strip().isdigit() or int(memory.stdout) < 9 * 1024**3:
            raise StandOperationError(
                f"Docker Ollama needs a 10 GiB VM. Stop the lab; run limactl edit {self._config.vm_name} --memory 10."
            )
        # A fresh VM needs the Compose definition before its first model start.
        DeploymentPreparationImpl(self._config, self._runner).transfer_files()
        self._runner.run(
            guest_arguments(
                self._config,
                "sudo",
                "install",
                "-d",
                "-m",
                "0700",
                "-o",
                "10000",
                "-g",
                "10000",
                "/srv/agent-lab/ollama",
            ),
            timeout=self._config.sync_timeout,
        )
        self._runner.run(
            compose_arguments(self._config, "up", "-d", "--no-deps", "--wait", "--wait-timeout", "90", "ollama"),
            timeout=self._config.image_build_timeout,
        )

    def wait_ready(self) -> None:
        deadline = time.monotonic() + self._config.readiness_timeout
        while (remaining := deadline - time.monotonic()) > 0:
            result = self._runner.capture(
                guest_arguments(self._config, "curl", "-fsS", "--max-time", "3", "http://127.0.0.1:11434/api/version"),
                timeout=min(self._config.probe_timeout, remaining),
                check=False,
            )
            # The HTTP endpoint must belong to the container that we inspected.
            remaining = deadline - time.monotonic()
            if (
                remaining > 0
                and result.returncode == 0
                and is_version_response(result.stdout)
                and self.is_started(timeout=min(self._config.probe_timeout, remaining))
            ):
                return
            time.sleep(min(self._config.poll_interval, max(0, deadline - time.monotonic())))
        raise StandOperationError("Docker Ollama did not become ready.", exit_code=124)

    def stop(self) -> None:
        # Stop even a failed/restarting container to disable its restart policy.
        if self._inspect() is not None:
            self._runner.run(
                guest_arguments(self._config, "sudo", "docker", "stop", "--timeout", "10", "agent-research-ollama"),
                timeout=self._config.vm_stop_timeout,
            )

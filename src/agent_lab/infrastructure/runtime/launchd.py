import os
import plistlib
import re
import time
from dataclasses import dataclass
from typing import Final, TypedDict

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.stand.components import StandComponent
from agent_lab.infrastructure.process import ProcessRunner
from agent_lab.infrastructure.runtime.config import RuntimeConfig

MISSING_SERVICE_EXIT_CODE: Final = 113
RESERVED_LABEL_EXIT_CODE: Final = 5


class LaunchAgent(TypedDict):
    Label: str
    ProgramArguments: list[str]
    EnvironmentVariables: dict[str, str]
    RunAtLoad: bool
    KeepAlive: bool
    ThrottleInterval: int
    StandardOutPath: str
    StandardErrorPath: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LaunchdSnapshot:
    loaded: bool
    pid: int | None = None


class LaunchdServicesImpl:
    def __init__(self, config: RuntimeConfig, runner: ProcessRunner) -> None:
        self._config = config
        self._runner = runner
        self._domain = f"gui/{os.getuid()}"

    def _target(self, component: StandComponent) -> str:
        return f"{self._domain}/local.agent-research-lab.{component}"

    def inspect(self, component: StandComponent, *, timeout: float | None = None) -> LaunchdSnapshot:
        result = self._runner.capture(
            ("launchctl", "print", self._target(component)),
            timeout=self._config.service_timeout if timeout is None else timeout,
            check=False,
        )
        if result.returncode == MISSING_SERVICE_EXIT_CODE and "Could not find service" in result.stderr:
            return LaunchdSnapshot(loaded=False)
        if result.returncode != 0:
            raise StandOperationError(f"Cannot inspect {component}: {result.stderr.strip()}")
        match = re.search(r"^\s*pid = ([1-9][0-9]*)\s*$", result.stdout, re.MULTILINE)
        return LaunchdSnapshot(loaded=True, pid=int(match[1]) if match else None)

    def start(self, component: StandComponent) -> None:
        directory = self._config.runtime_directory
        config = self._agent_config(component)
        try:
            for path in (directory, directory / "logs", directory / "ollama/models"):
                path.mkdir(parents=True, exist_ok=True, mode=0o700)
                path.chmod(0o700)
            plist = directory / f"{component}.plist"
            plist.write_bytes(plistlib.dumps(config))
            plist.chmod(0o600)
        except OSError as error:
            raise StandOperationError(f"Cannot configure {component}: {error.strerror}.") from error
        # A just-removed launchd job can temporarily reserve its label.
        for delay in (0.0, 0.25, 0.5, 1.0):
            if delay:
                time.sleep(delay)
            result = self._runner.capture(
                ("launchctl", "bootstrap", self._domain, str(plist)),
                timeout=self._config.service_timeout,
                check=False,
            )
            if result.returncode == 0:
                return
            if result.returncode != RESERVED_LABEL_EXIT_CODE:
                break
        raise StandOperationError(
            f"Cannot start {component}: {result.stderr.strip()}",
            exit_code=result.returncode if result.returncode > 0 else 128 - result.returncode,
        )

    def stop(self, component: StandComponent) -> None:
        if self.inspect(component).loaded:
            self._runner.run(("launchctl", "bootout", self._target(component)), timeout=self._config.service_timeout)

    def _agent_config(self, component: StandComponent) -> LaunchAgent:
        directory = self._config.runtime_directory
        if component == StandComponent.OLLAMA:
            arguments = ["/opt/homebrew/bin/ollama", "serve"]
            environment = {
                "OLLAMA_HOST": "127.0.0.1:11434",
                "OLLAMA_MODELS": str(directory / "ollama/models"),
                "OLLAMA_NO_CLOUD": "1",
                "OLLAMA_CONTEXT_LENGTH": "65536",
                "OLLAMA_NUM_PARALLEL": "1",
                "OLLAMA_MAX_LOADED_MODELS": "1",
                "OLLAMA_FLASH_ATTENTION": "1",
                "OLLAMA_KV_CACHE_TYPE": "q8_0",
                "OLLAMA_KEEP_ALIVE": "5m",
            }
        else:
            ssh_config = self._config.home_directory / ".lima" / self._config.vm_name / "ssh.config"
            if not ssh_config.is_file():
                raise StandOperationError(f"Start {self._config.vm_name} before creating the tunnel.")
            arguments = [
                "/usr/bin/ssh",
                "-F",
                str(ssh_config),
                "-o",
                "ForwardAgent=no",
                # The forward must belong to this job, not Lima's shared SSH master.
                "-o",
                "ControlMaster=no",
                "-o",
                "ControlPath=none",
                "-o",
                "ControlPersist=no",
                "-o",
                "ExitOnForwardFailure=yes",
                "-o",
                "ServerAliveInterval=15",
                "-o",
                "ServerAliveCountMax=3",
                "-N",
                "-T",
                "-R",
                "127.0.0.1:11434:127.0.0.1:11434",
                f"lima-{self._config.vm_name}",
            ]
            environment = {}
        return LaunchAgent(
            Label=f"local.agent-research-lab.{component}",
            ProgramArguments=arguments,
            EnvironmentVariables=environment,
            RunAtLoad=True,
            KeepAlive=True,
            ThrottleInterval=15,
            StandardOutPath=str(directory / f"logs/{component}.stdout.log"),
            StandardErrorPath=str(directory / f"logs/{component}.stderr.log"),
        )

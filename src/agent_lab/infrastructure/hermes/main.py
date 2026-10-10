from agent_lab.application.hermes.interfaces.runtime import (
    HermesChat,
    HermesGateway,
    HermesSetup,
    HermesWebDependencies,
)
from agent_lab.infrastructure.process import ProcessRunner
from agent_lab.infrastructure.runtime.commands import compose_arguments, guest_arguments
from agent_lab.infrastructure.runtime.config import RuntimeConfig


class HermesRuntimeImpl(HermesSetup, HermesWebDependencies, HermesChat, HermesGateway):
    def __init__(self, config: RuntimeConfig, runner: ProcessRunner) -> None:
        self._config = config
        self._runner = runner

    def setup(self) -> None:
        self._runner.interactive(
            compose_arguments(self._config, "run", "--rm", "hermes", "setup"),
            timeout=self._config.interactive_timeout,
        )

    def install_search_dependency(self) -> None:
        self._runner.interactive(
            compose_arguments(self._config, "run", "--rm", "hermes", "pm", "install", "--extra", "ddgs"),
            timeout=self._config.web_install_timeout,
        )

    def install_browser_dependency(self) -> None:
        self._runner.interactive(
            compose_arguments(self._config, "run", "--rm", "hermes", "pm", "install", "agent-browser"),
            timeout=self._config.web_install_timeout,
        )

    def chat(self, arguments: tuple[str, ...]) -> None:
        self._runner.interactive(
            compose_arguments(self._config, "run", "--rm", "hermes", "chat", *arguments),
            timeout=self._config.interactive_timeout,
        )

    def check_configuration(self) -> None:
        preflight = self._config.deployment_directory / "infra/hermes/preflight.py"
        self._runner.run(
            compose_arguments(
                self._config,
                "run",
                "--rm",
                "-v",
                f"{preflight}:/opt/preflight.py:ro",
                "hermes",
                "python",
                "/opt/preflight.py",
            ),
            timeout=self._config.gateway_timeout,
        )

    def check_model_connection(self) -> None:
        self._runner.run(
            guest_arguments(self._config, "curl", "-fsS", "--max-time", "5", "http://127.0.0.1:11434/api/version"),
            timeout=self._config.status_timeout,
        )

    def start_gateway(self) -> None:
        self._runner.run(compose_arguments(self._config, "up", "-d"), timeout=self._config.gateway_timeout)

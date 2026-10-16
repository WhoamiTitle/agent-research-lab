from agent_lab.application.model.interfaces.preparation import ModelPreparation
from agent_lab.infrastructure.process import ProcessRunner
from agent_lab.infrastructure.runtime.commands import compose_arguments
from agent_lab.infrastructure.runtime.config import OllamaBackend, RuntimeConfig


class LocalModelImpl(ModelPreparation):
    def __init__(self, config: RuntimeConfig, runner: ProcessRunner) -> None:
        self._config = config
        self._runner = runner

    def pull_base_model(self) -> None:
        arguments = (
            compose_arguments(self._config, "exec", "-T", "ollama", "ollama", "pull", "qwen3.5:4b")
            if self._config.ollama_backend == OllamaBackend.DOCKER
            else ("ollama", "pull", "qwen3.5:4b")
        )
        self._runner.interactive(arguments, timeout=self._config.model_pull_timeout)

    def create_lab_model(self) -> None:
        arguments = (
            compose_arguments(
                self._config, "exec", "-T", "ollama", "ollama", "create", "agent-lab-qwen:4b", "-f", "/opt/Modelfile"
            )
            if self._config.ollama_backend == OllamaBackend.DOCKER
            else (
                "ollama",
                "create",
                "agent-lab-qwen:4b",
                "-f",
                str(self._config.project_root / "infra/ollama/Modelfile"),
            )
        )
        self._runner.interactive(
            arguments,
            timeout=self._config.model_create_timeout,
        )

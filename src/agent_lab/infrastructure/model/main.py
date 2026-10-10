from agent_lab.application.model.interfaces.preparation import ModelPreparation
from agent_lab.infrastructure.process import ProcessRunner
from agent_lab.infrastructure.runtime.config import RuntimeConfig


class LocalModelImpl(ModelPreparation):
    def __init__(self, config: RuntimeConfig, runner: ProcessRunner) -> None:
        self._config = config
        self._runner = runner

    def pull_base_model(self) -> None:
        self._runner.interactive(("ollama", "pull", "qwen3.5:4b"), timeout=self._config.model_pull_timeout)

    def create_lab_model(self) -> None:
        self._runner.interactive(
            ("ollama", "create", "agent-lab-qwen:4b", "-f", str(self._config.project_root / "infra/ollama/Modelfile")),
            timeout=self._config.model_create_timeout,
        )

from agent_lab.application.deployment.interfaces.preparation import DeploymentPreparation
from agent_lab.application.hermes.interfaces.runtime import (
    HermesChat,
    HermesGateway,
    HermesSetup,
    HermesWebDependencies,
)
from agent_lab.application.model.interfaces.preparation import ModelPreparation


class PreparationMock(
    ModelPreparation, DeploymentPreparation, HermesSetup, HermesWebDependencies, HermesChat, HermesGateway
):
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def pull_base_model(self) -> None:
        self.calls.append(("pull", ()))

    def create_lab_model(self) -> None:
        self.calls.append(("create", ()))

    def transfer_files(self) -> None:
        self.calls.append(("transfer", ()))

    def prepare_guest(self) -> None:
        self.calls.append(("prepare", ()))

    def setup(self, *, gateway_only: bool = False) -> None:
        self.calls.append(("setup", ("gateway",) if gateway_only else ()))

    def install_search_dependency(self) -> None:
        self.calls.append(("search", ()))

    def install_browser_dependency(self) -> None:
        self.calls.append(("browser", ()))

    def chat(self, arguments: tuple[str, ...]) -> None:
        self.calls.append(("chat", arguments))

    def check_configuration(self) -> None:
        self.calls.append(("configuration", ()))

    def check_model_connection(self) -> None:
        self.calls.append(("connection", ()))

    def start_gateway(self) -> None:
        self.calls.append(("gateway", ()))

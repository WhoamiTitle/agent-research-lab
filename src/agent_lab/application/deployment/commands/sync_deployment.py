from agent_lab.application.deployment.interfaces.preparation import DeploymentPreparation


class SyncDeploymentHandler:
    def __init__(self, preparation: DeploymentPreparation) -> None:
        self._preparation = preparation

    def __call__(self) -> None:
        self._preparation.transfer_files()
        self._preparation.prepare_guest()

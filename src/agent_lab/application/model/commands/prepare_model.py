from agent_lab.application.model.interfaces.preparation import ModelPreparation


class PrepareModelHandler:
    def __init__(self, preparation: ModelPreparation) -> None:
        self._preparation = preparation

    def __call__(self) -> None:
        self._preparation.pull_base_model()
        self._preparation.create_lab_model()

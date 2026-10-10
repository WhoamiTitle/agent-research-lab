from typing import Protocol


class ModelPreparation(Protocol):
    """Bounded model operations; failures raise StandOperationError.

    Downloaded weights and an existing lab model are retained after failure.
    """

    def pull_base_model(self) -> None:
        raise NotImplementedError

    def create_lab_model(self) -> None:
        raise NotImplementedError

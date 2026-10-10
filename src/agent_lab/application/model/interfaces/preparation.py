from abc import abstractmethod
from typing import Protocol


class ModelPreparation(Protocol):
    """Bounded model operations; failures raise StandOperationError.

    Downloaded weights and an existing lab model are retained after failure.
    """

    @abstractmethod
    def pull_base_model(self) -> None: ...

    @abstractmethod
    def create_lab_model(self) -> None: ...

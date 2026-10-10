from abc import abstractmethod
from typing import Protocol


class DeploymentPreparation(Protocol):
    """Transfer reviewed files, seed missing data and install log retention.

    Operations are bounded and raise StandOperationError. Temporary host files
    are released on failure. Guest file changes are not transactional; existing
    configuration and memory must remain intact across retries.
    """

    @abstractmethod
    def transfer_files(self) -> None: ...

    @abstractmethod
    def prepare_guest(self) -> None: ...

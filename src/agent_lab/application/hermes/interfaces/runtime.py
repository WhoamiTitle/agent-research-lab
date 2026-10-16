from abc import abstractmethod
from typing import Protocol


class HermesSetup(Protocol):
    """Run the setup wizard with the caller's terminal and streams.

    The session has an explicit maximum duration, supports interruption and
    raises StandOperationError on external failure. Credentials stay in the VM.
    """

    @abstractmethod
    def setup(self, *, gateway_only: bool = False) -> None: ...


class HermesWebDependencies(Protocol):
    """Bounded dependency installation; failure preserves completed installs."""

    @abstractmethod
    def install_search_dependency(self) -> None: ...

    @abstractmethod
    def install_browser_dependency(self) -> None: ...


class HermesChat(Protocol):
    """Forward literal argv and terminal input to a bounded operator session.

    Errors raise StandOperationError; interruption releases the foreground
    command. Conversation data remains in the VM.
    """

    @abstractmethod
    def chat(self, arguments: tuple[str, ...]) -> None: ...


class HermesGateway(Protocol):
    """Bounded gateway operations; failures raise StandOperationError.

    Configuration and model connection must pass before starting the gateway.
    A failed start may have reached Docker; existing containers are retained.
    """

    @abstractmethod
    def check_configuration(self) -> None: ...

    @abstractmethod
    def check_model_connection(self) -> None: ...

    @abstractmethod
    def start_gateway(self) -> None: ...

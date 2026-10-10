from typing import Protocol


class HermesSetup(Protocol):
    """Run the setup wizard with the caller's terminal and streams.

    The session has an explicit maximum duration, supports interruption and
    raises StandOperationError on external failure. Credentials stay in the VM.
    """

    def setup(self) -> None:
        raise NotImplementedError


class HermesWebDependencies(Protocol):
    """Bounded dependency installation; failure preserves completed installs."""

    def install_search_dependency(self) -> None:
        raise NotImplementedError

    def install_browser_dependency(self) -> None:
        raise NotImplementedError


class HermesChat(Protocol):
    """Forward literal argv and terminal input to a bounded operator session.

    Errors raise StandOperationError; interruption releases the foreground
    command. Conversation data remains in the VM.
    """

    def chat(self, arguments: tuple[str, ...]) -> None:
        raise NotImplementedError


class HermesGateway(Protocol):
    """Bounded gateway operations; failures raise StandOperationError.

    Configuration and model connection must pass before starting the gateway.
    A failed start may have reached Docker; existing containers are retained.
    """

    def check_configuration(self) -> None:
        raise NotImplementedError

    def check_model_connection(self) -> None:
        raise NotImplementedError

    def start_gateway(self) -> None:
        raise NotImplementedError

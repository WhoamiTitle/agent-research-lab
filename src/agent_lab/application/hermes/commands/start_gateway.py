from agent_lab.application.hermes.interfaces.runtime import HermesGateway


class StartGatewayHandler:
    def __init__(self, runtime: HermesGateway) -> None:
        self._runtime = runtime

    def __call__(self) -> None:
        self._runtime.check_configuration()
        self._runtime.check_model_connection()
        self._runtime.start_gateway()

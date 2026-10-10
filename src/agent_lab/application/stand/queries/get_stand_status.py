from agent_lab.application.stand.interfaces.runtime import StandDiagnostics


class GetStandStatusHandler:
    """Show the existing status commands; this is not a readiness verdict."""

    def __init__(self, diagnostics: StandDiagnostics) -> None:
        self._diagnostics = diagnostics

    def __call__(self) -> None:
        self._diagnostics.show_vm_status()
        self._diagnostics.show_model_status()
        self._diagnostics.show_container_status()

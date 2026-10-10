from typing import override

from agent_lab.infrastructure.process import ProcessResult, ProcessRunner


class ReadinessRunnerMock(ProcessRunner):
    def __init__(self, *, response: str, pid: int | None = 123) -> None:
        self.calls: list[tuple[tuple[str, ...], float, bool]] = []
        self._response = response
        self._pid = pid

    @override
    def capture(self, arguments: tuple[str, ...], *, timeout: float, check: bool = True) -> ProcessResult:
        self.calls.append((arguments, timeout, check))
        output = self._response
        if arguments[0] == "launchctl":
            output = "job = {\n}" if self._pid is None else f"job = {{\n  pid = {self._pid}\n}}"
        return ProcessResult(returncode=0, stdout=output, stderr="")

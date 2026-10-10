class StandOperationError(Exception):
    """A failed external operation, represented without adapter-specific exceptions."""

    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code

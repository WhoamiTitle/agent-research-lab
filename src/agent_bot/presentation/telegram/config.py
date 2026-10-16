from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class TelegramConfig:
    token: str = field(repr=False)

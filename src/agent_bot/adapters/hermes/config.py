from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True, kw_only=True)
class HermesConfig:
    api_key: str = field(repr=False)
    base_url: str = "http://127.0.0.1:8642"
    request_timeout: float = 15.0
    run_timeout: float = 300.0
    poll_interval: float = 1.0
    conversation_key: str = "agent-lab-telegram-owner"

import json
import logging
from datetime import datetime
from typing import override
from zoneinfo import ZoneInfo


class JsonFormatter(logging.Formatter):
    def __init__(self, timezone: str) -> None:
        super().__init__()
        self._timezone = ZoneInfo(timezone)

    @override
    def format(self, record: logging.LogRecord) -> str:
        # Dependency exceptions may include Telegram URLs and message contents.
        event = record.getMessage() if record.name.startswith("agent_bot.") else "dependency_event"
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created, self._timezone).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "event": event,
            },
            ensure_ascii=False,
        )


def configure_logging(timezone: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(timezone))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    for name in ("aiogram", "aiohttp", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)

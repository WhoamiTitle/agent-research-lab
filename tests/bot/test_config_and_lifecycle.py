import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_bot.main.config.loader import load_config
from agent_bot.main.lock import BotAlreadyRunningError, single_process
from agent_bot.main.logs import JsonFormatter


@pytest.mark.parametrize("owner", ["", "42,43", "*", "0", "@fixture"])
def test_configuration_rejects_broad_or_invalid_owner(monkeypatch: pytest.MonkeyPatch, owner: str) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:fixture")
    monkeypatch.setenv("TELEGRAM_ALLOWED_USERS", owner)
    monkeypatch.setenv("HERMES_API_KEY", "fixture" * 8)

    with pytest.raises(ValueError, match="one numeric"):
        load_config()


def test_second_poller_cannot_own_same_directory(tmp_path: Path) -> None:
    with single_process(tmp_path), pytest.raises(BotAlreadyRunningError), single_process(tmp_path):
        pytest.fail("A second poller acquired the lock.")

    with single_process(tmp_path):
        assert (tmp_path / "polling.lock").is_file()


@pytest.mark.parametrize(("month", "offset"), [(1, "-08:00"), (10, "-07:00")])
def test_logs_use_los_angeles_offset_and_hide_dependency_messages(month: int, offset: str) -> None:
    record = logging.LogRecord("aiogram", logging.ERROR, __file__, 1, "private bot URL and user text", (), None)
    record.created = datetime(2026, month, 16, 17, tzinfo=UTC).timestamp()

    result = json.loads(JsonFormatter("America/Los_Angeles").format(record))

    assert result["timestamp"].endswith(offset)
    assert result["event"] == "dependency_event"
    assert "private" not in json.dumps(result)

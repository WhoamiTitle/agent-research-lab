import os
import stat
from pathlib import Path

import pytest

from infra.bot import setup
from infra.bot.setup import BotCredentials, PrivatePaths, configure_bot, prepare_private_files, read_environment

PRIVATE_MODE = 0o600
DUMMY_BOT_CREDENTIAL = "123:fixture"


@pytest.fixture
def private_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PrivatePaths:
    paths = PrivatePaths(backend=tmp_path / "data", bot=tmp_path / "bot", compose=tmp_path / "compose.yaml")
    paths.backend.mkdir()
    (paths.backend / ".env").write_text(
        "TELEGRAM_BOT_TOKEN=123:fixture\nTELEGRAM_ALLOWED_USERS=42\nLOCAL_OPTION=preserved\n"
    )
    (paths.backend / "config.yaml").write_text("existing configuration\n")
    (paths.backend / "config.yaml").chmod(0o640)

    def chown(path: Path, uid: int, gid: int) -> None:
        assert path.exists()
        assert uid >= 0
        assert gid >= 0

    monkeypatch.setattr(os, "chown", chown)
    return paths


def test_credentials_move_to_bot_and_repeat_keeps_shared_key(private_paths: PrivatePaths) -> None:
    credentials = BotCredentials(token=DUMMY_BOT_CREDENTIAL, owner_id="42")

    prepare_private_files(private_paths, credentials)
    backend = read_environment(private_paths.backend / ".env")
    frontend = read_environment(private_paths.bot / ".env")

    assert backend["TELEGRAM_BOT_TOKEN"] == ""
    assert backend["LOCAL_OPTION"] == "preserved"
    assert frontend["TELEGRAM_BOT_TOKEN"] == credentials.token
    assert frontend["TELEGRAM_ALLOWED_USERS"] == credentials.owner_id
    assert frontend["HERMES_API_KEY"] == backend["API_SERVER_KEY"]
    assert stat.S_IMODE((private_paths.bot / ".env").stat().st_mode) == PRIVATE_MODE

    prepare_private_files(private_paths, setup.saved_credentials(private_paths))

    assert read_environment(private_paths.bot / ".env")["HERMES_API_KEY"] == frontend["HERMES_API_KEY"]


def test_managed_config_failure_restores_credentials_and_configuration(
    private_paths: PrivatePaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    environment = (private_paths.backend / ".env").read_bytes()
    configuration = (private_paths.backend / "config.yaml").read_bytes()
    original_mode = stat.S_IMODE((private_paths.backend / "config.yaml").stat().st_mode)

    def fail(paths: PrivatePaths) -> None:
        (paths.backend / "config.yaml").write_text("partially changed configuration")
        raise ValueError("fixture configuration failure")

    monkeypatch.setattr(setup, "configure_hermes", fail)

    with pytest.raises(ValueError, match="fixture configuration failure"):
        configure_bot(private_paths, BotCredentials(token=DUMMY_BOT_CREDENTIAL, owner_id="42"))

    assert (private_paths.backend / ".env").read_bytes() == environment
    assert (private_paths.backend / "config.yaml").read_bytes() == configuration
    assert stat.S_IMODE((private_paths.backend / "config.yaml").stat().st_mode) == original_mode
    assert not (private_paths.bot / ".env").exists()
    assert list((private_paths.backend.parent / "backups").iterdir())

import argparse
import getpass
import json
import os
import re
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

MIN_API_KEY_LENGTH: Final = 32
OWNER_UID: Final = 10000
OWNER_GID: Final = 10000


@dataclass(frozen=True, slots=True, kw_only=True)
class PrivatePaths:
    backend: Path = Path("/srv/agent-lab/data")
    bot: Path = Path("/srv/agent-lab/bot")
    compose: Path = Path("/srv/agent-lab/deployment/infra/hermes/compose.yaml")


@dataclass(frozen=True, slots=True, kw_only=True)
class BotCredentials:
    token: str = field(repr=False)
    owner_id: str = field(repr=False)


@dataclass(frozen=True, slots=True, kw_only=True)
class FileSnapshot:
    path: Path
    contents: str | None = field(repr=False)
    mode: int = 0o600
    uid: int = OWNER_UID
    gid: int = OWNER_GID


def read_environment(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        parts = shlex.split(value, comments=True)
        if len(parts) > 1:
            raise ValueError("Invalid private environment value.")
        result[key.strip()] = parts[0] if parts else ""
    return result


def atomic_write(path: Path, contents: str, *, mode: int = 0o600, uid: int = OWNER_UID, gid: int = OWNER_GID) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(contents)
    try:
        os.chown(temporary, uid, gid)
        temporary.chmod(mode)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def updated_environment(path: Path, updates: dict[str, str]) -> str:
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    missing = set(updates)
    result = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else ""
        if key in updates:
            result.append(f"{key}={json.dumps(updates[key])}")
            missing.discard(key)
        else:
            result.append(line)
    result.extend(f"{key}={json.dumps(updates[key])}" for key in sorted(missing))
    return "\n".join(result) + "\n"


def saved_credentials(paths: PrivatePaths) -> BotCredentials:
    values = {
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_ALLOWED_USERS": "",
        **read_environment(paths.backend / ".env"),
    }
    bot = read_environment(paths.bot / ".env")
    for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USERS"):
        if bot.get(key):
            values[key] = bot[key]
    return BotCredentials(token=values["TELEGRAM_BOT_TOKEN"], owner_id=values["TELEGRAM_ALLOWED_USERS"])


def validate_credentials(credentials: BotCredentials) -> None:
    if re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", credentials.token) is None:
        raise ValueError("A dedicated Telegram bot token is required.")
    if re.fullmatch(r"[1-9][0-9]*", credentials.owner_id) is None:
        raise ValueError("Exactly one numeric Telegram owner is required.")


def prepare_private_files(paths: PrivatePaths, credentials: BotCredentials) -> None:
    validate_credentials(credentials)
    backend = {"API_SERVER_KEY": "", **read_environment(paths.backend / ".env")}
    api_key = backend["API_SERVER_KEY"] or secrets.token_urlsafe(48)
    if len(api_key) < MIN_API_KEY_LENGTH:
        raise ValueError("The existing Hermes API key is too short; replace it locally.")
    paths.bot.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chown(paths.bot, OWNER_UID, OWNER_GID)
    paths.bot.chmod(0o700)
    atomic_write(
        paths.bot / ".env",
        updated_environment(
            paths.bot / ".env",
            {
                "TELEGRAM_BOT_TOKEN": credentials.token,
                "TELEGRAM_ALLOWED_USERS": credentials.owner_id,
                "HERMES_API_KEY": api_key,
                "TELEGRAM_ALLOW_ALL_USERS": "false",
                "GATEWAY_ALLOW_ALL_USERS": "false",
                "GATEWAY_ALLOWED_USERS": "",
                "TELEGRAM_GUEST_MODE": "false",
                "TELEGRAM_GROUP_ALLOWED_USERS": "",
                "TELEGRAM_GROUP_ALLOWED_CHATS": "",
            },
        ),
    )
    atomic_write(
        paths.backend / ".env",
        updated_environment(
            paths.backend / ".env",
            {
                "API_SERVER_KEY": api_key,
                "TELEGRAM_BOT_TOKEN": "",
                "TELEGRAM_ALLOWED_USERS": "",
                "TELEGRAM_HOME_CHANNEL": "",
            },
        ),
    )


def configure_hermes(paths: PrivatePaths) -> None:
    executable = shutil.which("docker")
    if executable is None:
        raise FileNotFoundError("Docker is required inside the lab VM.")
    command = (
        executable,
        "compose",
        "-f",
        str(paths.compose),
        "run",
        "--rm",
        "--no-deps",
        "--user",
        "10000:10000",
        "--entrypoint",
        "/opt/hermes/bin/hermes",
        "hermes",
    )
    # The gateway activates a managed environment, separate from the image's base venv.
    result = subprocess.run(
        (*command, "pm", "install", "--extra", "messaging"),
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("Could not prepare the Hermes API dependencies; retry private setup.")
    fields = (
        ("platforms.telegram.enabled", "false"),
        ("platforms.api_server.enabled", "true"),
        ("platforms.api_server.extra.host", "127.0.0.1"),
        ("platforms.api_server.extra.port", "8642"),
        ("gateway.api_server.max_concurrent_runs", "1"),
    )
    for key, value in fields:
        result = subprocess.run(
            (*command, "config", "set", key, value),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            raise ValueError(f"Could not configure Hermes setting {key}; restore the private backup before startup.")


def configure_bot(paths: PrivatePaths, credentials: BotCredentials) -> None:
    validate_credentials(credentials)
    snapshots = []
    for path in (paths.backend / ".env", paths.backend / "config.yaml", paths.bot / ".env"):
        if path.is_file():
            metadata = path.stat()
            snapshots.append(
                FileSnapshot(
                    path=path,
                    contents=path.read_text(encoding="utf-8"),
                    mode=stat.S_IMODE(metadata.st_mode),
                    uid=metadata.st_uid,
                    gid=metadata.st_gid,
                )
            )
        else:
            snapshots.append(FileSnapshot(path=path, contents=None))
    backup_root = paths.backend.parent / "backups"
    backup_root.mkdir(mode=0o700, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix="bot-setup-", dir=backup_root))
    for index, snapshot in enumerate(snapshots):
        if snapshot.contents is not None:
            target = backup / f"{index}-{snapshot.path.name}"
            target.write_text(snapshot.contents, encoding="utf-8")
            target.chmod(0o600)
    complete = False
    try:
        prepare_private_files(paths, credentials)
        configure_hermes(paths)
        complete = True
    finally:
        if not complete:
            for snapshot in snapshots:
                if snapshot.contents is None:
                    snapshot.path.unlink(missing_ok=True)
                else:
                    atomic_write(
                        snapshot.path, snapshot.contents, mode=snapshot.mode, uid=snapshot.uid, gid=snapshot.gid
                    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure the custom Telegram bot; credentials stay inside the VM.")
    parser.add_argument("--migrate-existing", action="store_true", help="Use credentials previously saved by Hermes")
    arguments = parser.parse_args()
    paths = PrivatePaths()
    try:
        credentials = saved_credentials(paths)
        if not arguments.migrate_existing:
            token = getpass.getpass("Telegram bot token (Enter keeps the saved value): ").strip()
            owner_id = getpass.getpass("Your numeric Telegram ID (Enter keeps the saved value): ").strip()
            credentials = BotCredentials(token=token or credentials.token, owner_id=owner_id or credentials.owner_id)
        configure_bot(paths, credentials)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print(f"Bot setup failed: {error}", file=sys.stderr)
        return 1
    print("Bot credentials saved in the VM. Native Telegram disabled; local Hermes API configured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

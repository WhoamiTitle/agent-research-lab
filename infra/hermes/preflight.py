"""Refuse gateway startup until the local model and private Telegram setup are explicit."""

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

def main() -> int:
    data = Path("/opt/data")
    # Let Hermes interpret its own YAML using its managed dependency runtime.
    # The standalone Python in the official image intentionally lacks PyYAML.
    config = {}
    for field in ("model", "fallback_providers", "gateway.platforms.telegram"):
        result = subprocess.run(
            ["hermes", "config", "get", "--json", field],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        config[field] = json.loads(result.stdout)
    model = config["model"]
    if model["provider"] != "custom" or model["base_url"] != "http://127.0.0.1:11434/v1":
        raise ValueError("Only the explicitly selected local Ollama endpoint is allowed.")
    if "fallback_providers" in config and config["fallback_providers"]:
        raise ValueError("Cloud fallback has not been authorized.")
    if model["context_length"] < 64000:
        raise ValueError("Configured context is below the assignment requirement.")

    # Read only Telegram's simple string values without executing the .env.
    env: dict[str, str] = {}
    for line in (data / ".env").read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        field, raw_value = line.split("=", 1)
        field = field.strip()
        if field.startswith("TELEGRAM_"):
            parts = shlex.split(raw_value, comments=True)
            if len(parts) > 1:
                raise ValueError("Invalid Telegram value in private .env.")
            env[field] = parts[0] if parts else ""
    user_id = env["TELEGRAM_ALLOWED_USERS"] if "TELEGRAM_ALLOWED_USERS" in env else ""
    token = env["TELEGRAM_BOT_TOKEN"] if "TELEGRAM_BOT_TOKEN" in env else ""
    if not user_id or not re.fullmatch(r"[1-9][0-9]*", user_id):
        raise ValueError("Set exactly your own numeric TELEGRAM_ALLOWED_USERS in the private .env.")
    if not token or not re.fullmatch(r"[0-9]+:[A-Za-z0-9_-]+", token):
        raise ValueError("Set the dedicated bot token in the private .env.")
    for field in ("TELEGRAM_ALLOW_ALL", "TELEGRAM_GUEST_MODE"):
        value = env[field] if field in env else "false"
        if value is None or value.lower() not in {"false", "0", "no"}:
            raise ValueError(f"{field} must be explicitly disabled.")
    for field in ("TELEGRAM_GROUP_ALLOWED_USERS", "TELEGRAM_GROUP_ALLOWED_CHATS"):
        if field in env and env[field]:
            raise ValueError("This lab permits only the owner, without group access.")
    telegram = config["gateway.platforms.telegram"]
    if not telegram["enabled"]:
        raise ValueError("Enable the Telegram platform only after the private setup is complete.")
    extra = telegram["extra"] if "extra" in telegram else {}
    if "guest_mode" in extra and extra["guest_mode"]:
        raise ValueError("Telegram guest mode is forbidden for this lab.")
    for field in ("allow_from", "group_allow_from", "group_allowed_chats"):
        if field in extra and extra[field] not in ([], [user_id]):
            raise ValueError(f"Unexpected Telegram access in {field}.")
    print("Gateway configuration passed local preflight. Test outsider rejection separately.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"Gateway is not ready: {error}", file=sys.stderr)
        raise SystemExit(1)

import grp
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

PRIVATE_FILE_MODE: Final = 0o600
PRIVATE_DIRECTORY_MODE: Final = 0o700
SYSTEM_FILE_MODE: Final = 0o644
EXECUTABLE_MODE: Final = 0o755
SYSTEMCTL_TIMEOUT: Final = 30.0


@dataclass(frozen=True, slots=True, kw_only=True)
class GuestPaths:
    deployment: Path = Path("/srv/agent-lab/deployment")
    data: Path = Path("/srv/agent-lab/data")
    logrotate: Path = Path("/etc/logrotate.d")
    sbin: Path = Path("/usr/local/sbin")
    systemd: Path = Path("/etc/systemd/system")


@dataclass(frozen=True, slots=True, kw_only=True)
class FileOwner:
    uid: int
    gid: int


def install_file(source: Path, destination: Path, *, owner: FileOwner, mode: int) -> None:
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".agent-lab-", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        shutil.copyfile(source, temporary_path)
        os.chown(temporary_path, owner.uid, owner.gid)
        temporary_path.chmod(mode)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def seed_file(source: Path, destination: Path, *, owner: FileOwner) -> None:
    if not destination.is_file():
        install_file(source, destination, owner=owner, mode=PRIVATE_FILE_MODE)


def prepare_files(paths: GuestPaths, owner: FileOwner) -> None:
    seed_file(paths.deployment / "infra/hermes/config.yaml", paths.data / "config.yaml", owner=owner)
    seed_file(paths.deployment / "templates/hermes.env.example", paths.data / ".env", owner=owner)
    for directory in ("memories", "workspace", "logs", "logs/gateways", "skills", "skills/lab-readiness"):
        target = paths.data / directory
        target.mkdir(exist_ok=True)
        os.chown(target, owner.uid, owner.gid)
        target.chmod(PRIVATE_DIRECTORY_MODE)
    for memory in ("USER.md", "MEMORY.md"):
        seed_file(paths.deployment / "templates/memory" / memory, paths.data / "memories" / memory, owner=owner)
    install_file(
        paths.deployment / "templates/skills/lab-readiness/SKILL.md",
        paths.data / "skills/lab-readiness/SKILL.md",
        owner=owner,
        mode=PRIVATE_FILE_MODE,
    )
    system_owner = FileOwner(uid=os.geteuid(), gid=os.getegid())
    for source, destination, mode in (
        ("logrotate.conf", paths.logrotate / "agent-research-lab", SYSTEM_FILE_MODE),
        ("expire-gateway-logs.sh", paths.sbin / "agent-lab-expire-gateway-logs", EXECUTABLE_MODE),
        ("log-retention.service", paths.systemd / "agent-lab-log-retention.service", SYSTEM_FILE_MODE),
        ("log-retention.timer", paths.systemd / "agent-lab-log-retention.timer", SYSTEM_FILE_MODE),
    ):
        install_file(paths.deployment / "infra/hermes" / source, destination, owner=system_owner, mode=mode)


def main() -> int:
    try:
        owner = FileOwner(uid=pwd.getpwnam("researcher").pw_uid, gid=grp.getgrnam("researcher").gr_gid)
        prepare_files(GuestPaths(), owner)
        subprocess.run(("/usr/bin/systemctl", "daemon-reload"), check=True, timeout=SYSTEMCTL_TIMEOUT)
        subprocess.run(
            ("/usr/bin/systemctl", "enable", "--now", "agent-lab-log-retention.timer"),
            check=True,
            timeout=SYSTEMCTL_TIMEOUT,
        )
    except KeyError:
        sys.stderr.write("The researcher account and group are required.\n")
        return 1
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"systemctl: timeout after {SYSTEMCTL_TIMEOUT:g}s.\n")
        return 124
    except subprocess.CalledProcessError as error:
        return error.returncode if error.returncode >= 0 else 128 - error.returncode
    except OSError as error:
        sys.stderr.write(f"Guest provisioning: {error}.\n")
        return 126
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

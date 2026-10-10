import os
import shutil
from pathlib import Path

from infra.hermes.provision import FileOwner, GuestPaths


def build_guest_paths(directory: Path) -> GuestPaths:
    paths = GuestPaths(
        deployment=directory / "deployment",
        data=directory / "data",
        logrotate=directory / "etc/logrotate.d",
        sbin=directory / "usr/local/sbin",
        systemd=directory / "etc/systemd/system",
    )
    project = Path(__file__).resolve().parents[2]
    shutil.copytree(project / "infra/hermes", paths.deployment / "infra/hermes")
    shutil.copytree(project / "templates", paths.deployment / "templates")
    for target in (paths.data, paths.logrotate, paths.sbin, paths.systemd):
        target.mkdir(parents=True)
    return paths


def current_owner() -> FileOwner:
    return FileOwner(uid=os.geteuid(), gid=os.getegid())

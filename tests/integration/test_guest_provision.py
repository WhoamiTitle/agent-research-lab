import stat
from pathlib import Path
from typing import Final

from infra.hermes.provision import prepare_files
from tests.fixtures.guest import build_guest_paths, current_owner

EXPECTED_PRIVATE_FILE_MODE: Final = 0o600
EXPECTED_PRIVATE_DIRECTORY_MODE: Final = 0o700
EXPECTED_EXECUTABLE_MODE: Final = 0o755
EXPECTED_SYSTEM_FILE_MODE: Final = 0o644


def test_new_guest_files_keep_private_permissions_and_log_retention(tmp_path: Path) -> None:
    paths, owner = build_guest_paths(tmp_path), current_owner()

    prepare_files(paths, owner)

    for filename in ("config.yaml", ".env", "memories/USER.md", "memories/MEMORY.md", "skills/lab-readiness/SKILL.md"):
        target = paths.data / filename
        assert stat.S_IMODE(target.stat().st_mode) == EXPECTED_PRIVATE_FILE_MODE
        assert (target.stat().st_uid, target.stat().st_gid) == (owner.uid, owner.gid)
    for directory in ("memories", "workspace", "logs", "logs/gateways", "skills", "skills/lab-readiness"):
        assert stat.S_IMODE((paths.data / directory).stat().st_mode) == EXPECTED_PRIVATE_DIRECTORY_MODE
    assert stat.S_IMODE((paths.sbin / "agent-lab-expire-gateway-logs").stat().st_mode) == EXPECTED_EXECUTABLE_MODE
    assert stat.S_IMODE((paths.logrotate / "agent-research-lab").stat().st_mode) == EXPECTED_SYSTEM_FILE_MODE
    assert (paths.systemd / "agent-lab-log-retention.service").is_file()
    assert (paths.systemd / "agent-lab-log-retention.timer").is_file()


def test_repeated_sync_preserves_existing_configuration_memory_and_logs(tmp_path: Path) -> None:
    paths, owner = build_guest_paths(tmp_path), current_owner()
    prepare_files(paths, owner)
    preserved_files = ("config.yaml", ".env", "memories/USER.md", "memories/MEMORY.md", "logs/kept.log")
    snapshots: dict[str, tuple[bytes, int, int]] = {}
    for filename in preserved_files:
        target = paths.data / filename
        target.write_text(f"user content for {filename}", encoding="utf-8")
        target.chmod(0o640)
        snapshots[filename] = (target.read_bytes(), target.stat().st_mtime_ns, stat.S_IMODE(target.stat().st_mode))
    (paths.deployment / "templates/skills/lab-readiness/SKILL.md").write_text(
        "updated readiness skill", encoding="utf-8"
    )

    prepare_files(paths, owner)

    for filename, expected in snapshots.items():
        target = paths.data / filename
        assert (target.read_bytes(), target.stat().st_mtime_ns, stat.S_IMODE(target.stat().st_mode)) == expected
    assert (paths.data / "skills/lab-readiness/SKILL.md").read_text() == "updated readiness skill"


def test_skill_update_replaces_destination_symlink_without_overwriting_target(tmp_path: Path) -> None:
    paths, owner = build_guest_paths(tmp_path), current_owner()
    prepare_files(paths, owner)
    target = tmp_path / "kept-file"
    target.write_text("existing unrelated content", encoding="utf-8")
    skill = paths.data / "skills/lab-readiness/SKILL.md"
    skill.unlink()
    skill.symlink_to(target)

    prepare_files(paths, owner)

    assert target.read_text() == "existing unrelated content"
    assert not skill.is_symlink()
    assert skill.read_bytes() == (paths.deployment / "templates/skills/lab-readiness/SKILL.md").read_bytes()
    assert not list(skill.parent.glob(".agent-lab-*"))

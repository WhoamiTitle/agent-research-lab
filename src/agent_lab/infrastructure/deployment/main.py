import tarfile
import tempfile
from pathlib import PurePosixPath

from agent_lab.application.common.exceptions import StandOperationError
from agent_lab.application.deployment.interfaces.preparation import DeploymentPreparation
from agent_lab.infrastructure.process import ProcessRunner
from agent_lab.infrastructure.runtime.commands import guest_arguments
from agent_lab.infrastructure.runtime.config import RuntimeConfig


def reviewed_archive_member(member: tarfile.TarInfo) -> tarfile.TarInfo | None:
    if "__pycache__" in PurePosixPath(member.name).parts or member.name.endswith(".pyc"):
        return None
    return member


class DeploymentPreparationImpl(DeploymentPreparation):
    def __init__(self, config: RuntimeConfig, runner: ProcessRunner) -> None:
        self._config = config
        self._runner = runner

    def transfer_files(self) -> None:
        try:
            with tempfile.TemporaryFile() as source:
                with tarfile.open(fileobj=source, mode="w") as archive:
                    for directory in (
                        "infra/hermes",
                        "infra/bot",
                        "infra/ollama",
                        "templates",
                        "src/agent_bot",
                        "pyproject.toml",
                        "uv.lock",
                        ".dockerignore",
                    ):
                        archive.add(
                            self._config.project_root / directory,
                            arcname=directory,
                            filter=reviewed_archive_member,
                        )
                source.seek(0)
                self._runner.run_with_input(
                    guest_arguments(
                        self._config,
                        "sudo",
                        "tar",
                        "-xf",
                        "-",
                        "-C",
                        str(self._config.deployment_directory),
                    ),
                    source=source,
                    timeout=self._config.sync_timeout,
                )
        except (OSError, tarfile.TarError) as error:
            raise StandOperationError(f"Deployment archive: {error}.", exit_code=126) from error

    def prepare_guest(self) -> None:
        self._runner.run(
            guest_arguments(
                self._config,
                "sudo",
                "python3",
                str(self._config.deployment_directory / "infra/hermes/provision.py"),
            ),
            timeout=self._config.sync_timeout,
        )

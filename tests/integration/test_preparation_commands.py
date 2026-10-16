import shutil
import tarfile
from typing import Final

import pytest

from tests.fixtures.lab import LabShell

COMPOSE: Final = (
    "limactl",
    "shell",
    "agent-research",
    "--",
    "sudo",
    "docker",
    "compose",
    "-f",
    "/srv/agent-lab/deployment/infra/hermes/compose.yaml",
)
FAILURE_EXIT_CODE: Final = 19
LOCAL_FILE_FAILURE_EXIT_CODE: Final = 126


def test_model_preserves_pull_create_order_and_path_with_spaces(lab_shell: LabShell) -> None:
    result = lab_shell.run(("model",))

    assert result.returncode == 0, result.stderr
    assert lab_shell.commands() == [
        ["ollama", "pull", "qwen3.5:4b"],
        ["ollama", "create", "agent-lab-qwen:4b", "-f", str(lab_shell.project / "infra/ollama/Modelfile")],
    ]


@pytest.mark.parametrize(
    ("arguments", "section"),
    [
        (("setup",), ()),
        (("setup", "--gateway-only"), ("gateway",)),
    ],
)
def test_setup_preserves_compose_invocation(
    lab_shell: LabShell,
    arguments: tuple[str, ...],
    section: tuple[str, ...],
) -> None:
    result = lab_shell.run(arguments)

    assert result.returncode == 0, result.stderr
    if section:
        assert lab_shell.commands() == [
            [
                "limactl",
                "shell",
                "agent-research",
                "--",
                "sudo",
                "python3",
                "/srv/agent-lab/deployment/infra/bot/setup.py",
            ]
        ]
    else:
        assert lab_shell.commands() == [[*COMPOSE, "run", "--rm", "hermes", "setup"]]


def test_web_dependencies_preserve_install_order(lab_shell: LabShell) -> None:
    result = lab_shell.run(("web-deps",))

    assert result.returncode == 0, result.stderr
    assert lab_shell.commands() == [
        [*COMPOSE, "run", "--rm", "hermes", "pm", "install", "--extra", "ddgs"],
        [*COMPOSE, "run", "--rm", "hermes", "pm", "install", "agent-browser"],
    ]


def test_gateway_checks_configuration_and_connection_before_start(lab_shell: LabShell) -> None:
    (lab_shell.provider_directory / "ollama-tunnel").write_text("42")

    result = lab_shell.run(("gateway",))

    assert result.returncode == 0, result.stderr
    assert lab_shell.commands() == [
        [
            *COMPOSE,
            "run",
            "--rm",
            "--no-deps",
            "--user",
            "10000:10000",
            "--entrypoint",
            "/opt/hermes/.venv/bin/python3",
            "-v",
            "/srv/agent-lab/deployment/infra/hermes/preflight.py:/opt/preflight.py:ro",
            "-v",
            "/srv/agent-lab/bot:/opt/bot:ro",
            "hermes",
            "/opt/preflight.py",
        ],
        [
            "limactl",
            "shell",
            "agent-research",
            "--",
            "curl",
            "-fsS",
            "--max-time",
            "5",
            "http://127.0.0.1:11434/api/version",
        ],
        [*COMPOSE, "up", "-d", "--build", "--wait", "--wait-timeout", "90"],
    ]


def test_sync_transfers_only_deployment_files_and_skips_python_cache(lab_shell: LabShell) -> None:
    (lab_shell.project / ".env").write_text("fixture-private-data")
    (lab_shell.project / "infra/lima").mkdir()
    (lab_shell.project / "infra/lima/private-file").touch()
    cache = lab_shell.project / "infra/hermes/__pycache__"
    cache.mkdir()
    (cache / "cached.pyc").touch()
    (lab_shell.project / "templates/cached.pyc").touch()

    result = lab_shell.run(("sync",))

    assert result.returncode == 0, result.stderr
    with tarfile.open(lab_shell.provider_directory / "deployment.tar") as archive:
        names = archive.getnames()
    assert "infra/hermes/compose.yaml" in names
    assert "templates/hermes.env.example" in names
    assert "templates/memory/MEMORY.md" in names
    assert "templates/skills/lab-readiness/SKILL.md" in names
    assert "src/agent_bot/main/telegram.py" in names
    assert "infra/bot/Dockerfile" in names
    assert all(
        name.startswith(("infra/hermes", "infra/bot", "templates", "src/agent_bot"))
        or name in {"pyproject.toml", "uv.lock", ".dockerignore"}
        for name in names
    )
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
    assert lab_shell.commands()[0] == [
        "limactl",
        "shell",
        "agent-research",
        "--",
        "sudo",
        "tar",
        "-xf",
        "-",
        "-C",
        "/srv/agent-lab/deployment",
    ]
    assert lab_shell.commands()[1:] == [
        [
            "limactl",
            "shell",
            "agent-research",
            "--",
            "sudo",
            "python3",
            "/srv/agent-lab/deployment/infra/hermes/provision.py",
        ]
    ]


@pytest.mark.parametrize(
    ("command", "failed_step"),
    [
        ("model", 1),
        ("model", 2),
        ("sync", 1),
        ("sync", 2),
        ("setup", 1),
        ("web-deps", 1),
        ("web-deps", 2),
        ("gateway", 1),
        ("gateway", 2),
        ("gateway", 3),
    ],
)
def test_preparation_failure_preserves_exit_code_and_stops_next_steps(
    lab_shell: LabShell,
    command: str,
    failed_step: int,
) -> None:
    (lab_shell.provider_directory / "ollama-tunnel").write_text("42")

    result = lab_shell.run((command,), fail_call=failed_step, exit_code=FAILURE_EXIT_CODE)

    assert result.returncode == FAILURE_EXIT_CODE
    assert len(lab_shell.commands()) == failed_step


def test_chat_preserves_literal_arguments_without_shell_expansion(lab_shell: LabShell) -> None:
    question = 'two words; $(touch unexpected) "quotes"'

    result = lab_shell.run(("chat", "--oneshot", "-q", question, "--", "--help"))

    assert result.returncode == 0, result.stderr
    assert lab_shell.commands() == [
        [*COMPOSE, "run", "--rm", "hermes", "chat", "--oneshot", "-q", question, "--", "--help"]
    ]
    assert not (lab_shell.directory / "unexpected").exists()


@pytest.mark.parametrize("command", ["model", "sync", "setup", "web-deps", "gateway"])
def test_non_chat_preparation_commands_keep_ignoring_extra_arguments(lab_shell: LabShell, command: str) -> None:
    (lab_shell.provider_directory / "ollama-tunnel").write_text("42")

    result = lab_shell.run((command, "ignored", "--help"))

    assert result.returncode == 0, result.stderr
    assert not any("ignored" in arguments or "--help" in arguments for arguments in lab_shell.commands())


def test_missing_templates_fail_before_any_guest_transfer(lab_shell: LabShell) -> None:
    shutil.rmtree(lab_shell.project / "templates")

    result = lab_shell.run(("sync",))

    assert result.returncode == LOCAL_FILE_FAILURE_EXIT_CODE
    assert "Deployment archive:" in result.stderr
    assert "Traceback" not in result.stderr
    assert lab_shell.commands() == []
    assert not (lab_shell.provider_directory / "deployment.tar").exists()

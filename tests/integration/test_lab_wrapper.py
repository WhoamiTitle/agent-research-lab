import shlex
from concurrent.futures import ThreadPoolExecutor
from typing import Final

import pytest

from tests.fixtures.lab import LabShell

SERVICES_FAILURE_EXIT_CODE: Final = 9
STATUS_FAILURE_EXIT_CODE: Final = 13
EXISTING_MODEL_PID: Final = 42


def test_new_vm_start_preserves_template_path_with_spaces(lab_shell: LabShell) -> None:
    result = lab_shell.run(("start",))
    assert result.returncode == 0, result.stderr
    assert [command for command in lab_shell.commands() if command[1] == "start"] == [
        [
            "limactl",
            "start",
            "--tty=false",
            "--name=agent-research",
            str(lab_shell.project / "infra/lima/agent-lab.yaml"),
        ],
    ]
    assert lab_shell.pid("ollama") > 0
    assert lab_shell.pid("ollama-tunnel") > 0


def test_existing_vm_start_preserves_instance_name(lab_shell: LabShell) -> None:
    (lab_shell.home / ".lima/agent-research").mkdir(parents=True)
    result = lab_shell.run(("start",))
    assert result.returncode == 0, result.stderr
    assert [command for command in lab_shell.commands() if command[1] == "start"] == [
        ["limactl", "start", "--tty=false", "agent-research"],
    ]


@pytest.mark.parametrize("operation", ["vm-start", "bootstrap-ollama", "bootstrap-ollama-tunnel"])
def test_start_failure_after_creation_cleans_owned_resources(lab_shell: LabShell, operation: str) -> None:
    result = lab_shell.run(("start",), failures=(operation,), exit_code=SERVICES_FAILURE_EXIT_CODE)
    assert result.returncode == SERVICES_FAILURE_EXIT_CODE
    assert (lab_shell.provider_directory / "vm-status").read_text() == "Stopped"
    assert not (lab_shell.provider_directory / "ollama").exists()
    assert not (lab_shell.provider_directory / "ollama-tunnel").exists()
    assert (lab_shell.home / ".lima/agent-research/ssh.config").is_file()
    assert "Traceback" not in result.stderr


def test_repeated_start_preserves_pids_without_lifecycle_mutations(lab_shell: LabShell) -> None:
    first = lab_shell.run(("start",))
    assert first.returncode == 0, first.stderr
    model_pid, tunnel_pid = lab_shell.pid("ollama"), lab_shell.pid("ollama-tunnel")

    repeated = lab_shell.run(("start",))

    assert repeated.returncode == 0, repeated.stderr
    assert (lab_shell.pid("ollama"), lab_shell.pid("ollama-tunnel")) == (model_pid, tunnel_pid)
    assert not any(command[1] in {"start", "stop", "bootstrap", "bootout"} for command in lab_shell.commands())


def test_failed_tunnel_start_keeps_existing_vm_model_and_data(lab_shell: LabShell) -> None:
    vm_directory = lab_shell.home / ".lima/agent-research"
    vm_directory.mkdir(parents=True)
    (vm_directory / "ssh.config").write_text("# fixture\n")
    (lab_shell.provider_directory / "vm-status").write_text("Running")
    (lab_shell.provider_directory / "ollama").write_text(str(EXISTING_MODEL_PID))
    model_data = lab_shell.home / ".local/share/agent-research-lab/ollama/models/kept-model"
    model_data.parent.mkdir(parents=True)
    model_data.write_text("existing model data")

    result = lab_shell.run(("start",), failures=("bootstrap-ollama-tunnel",))

    assert result.returncode != 0
    assert (lab_shell.provider_directory / "vm-status").read_text() == "Running"
    assert lab_shell.pid("ollama") == EXISTING_MODEL_PID
    assert not (lab_shell.provider_directory / "ollama-tunnel").exists()
    assert model_data.read_text() == "existing model data"


def test_cleanup_failure_is_reported_and_other_resources_are_released(lab_shell: LabShell) -> None:
    result = lab_shell.run(("start",), failures=("bootstrap-ollama-tunnel", "bootout-ollama"))

    assert result.returncode != 0
    assert "Cleanup failed for ollama:" in result.stderr
    assert (lab_shell.provider_directory / "vm-status").read_text() == "Stopped"
    assert not (lab_shell.provider_directory / "ollama-tunnel").exists()
    assert (lab_shell.provider_directory / "ollama").exists()


def test_unmanaged_ollama_is_not_adopted_or_stopped(lab_shell: LabShell) -> None:
    (lab_shell.provider_directory / "external-api").touch()

    result = lab_shell.run(("start",))

    assert result.returncode != 0
    assert "outside the lab" in result.stderr
    assert (lab_shell.provider_directory / "external-api").exists()
    assert not any(command[1] in {"bootstrap", "bootout"} for command in lab_shell.commands())


def test_two_concurrent_starts_create_each_component_once(lab_shell: LabShell) -> None:
    lab_shell.environment["LAB_TEST_VM_START_DELAY"] = "0.5"
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(lab_shell.run, ("start",), reset_trace=False) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]

    assert all(result.returncode == 0 for result in results), [result.stderr for result in results]
    mutations = [command for command in lab_shell.commands() if command[1] in {"start", "bootstrap"}]
    assert [command[1] for command in mutations] == ["start", "bootstrap", "bootstrap"]


def test_explicit_stop_releases_components_and_retains_vm_files(lab_shell: LabShell) -> None:
    started = lab_shell.run(("start",))
    assert started.returncode == 0, started.stderr

    stopped = lab_shell.run(("stop",))

    assert stopped.returncode == 0, stopped.stderr
    assert (lab_shell.provider_directory / "vm-status").read_text() == "Stopped"
    assert not (lab_shell.provider_directory / "ollama").exists()
    assert not (lab_shell.provider_directory / "ollama-tunnel").exists()
    assert (lab_shell.home / ".lima/agent-research/ssh.config").is_file()


def test_status_preserves_commands_and_output(lab_shell: LabShell) -> None:
    result = lab_shell.run(("status",))
    assert result.returncode == 0, result.stderr
    expected = [
        ["limactl", "list", "agent-research"],
        ["ollama", "ps"],
        [
            "limactl",
            "shell",
            "agent-research",
            "--",
            "sudo",
            "docker",
            "compose",
            "-f",
            "/srv/agent-lab/deployment/infra/hermes/compose.yaml",
            "ps",
            "--all",
        ],
    ]
    assert lab_shell.commands() == expected
    assert result.stdout.splitlines() == [shlex.join(command) for command in expected]


@pytest.mark.parametrize("failed_step", [1, 2, 3])
def test_status_preserves_failure_codes_and_stops_probing(lab_shell: LabShell, failed_step: int) -> None:
    result = lab_shell.run(("status",), fail_call=failed_step, exit_code=STATUS_FAILURE_EXIT_CODE)
    assert result.returncode == STATUS_FAILURE_EXIT_CODE
    assert len(lab_shell.commands()) == failed_step


def test_chat_arguments_still_pass_directly_to_hermes(lab_shell: LabShell) -> None:
    result = lab_shell.run(("chat", "--oneshot", "-q", "two words"))
    assert result.returncode == 0, result.stderr
    assert lab_shell.commands() == [
        [
            "limactl",
            "shell",
            "agent-research",
            "--",
            "sudo",
            "docker",
            "compose",
            "-f",
            "/srv/agent-lab/deployment/infra/hermes/compose.yaml",
            "run",
            "--rm",
            "hermes",
            "chat",
            "--oneshot",
            "-q",
            "two words",
        ],
    ]


@pytest.mark.parametrize("arguments", [(), ("help",), ("unknown",)])
def test_wrapper_help_and_unknown_command_keep_usage(lab_shell: LabShell, arguments: tuple[str, ...]) -> None:
    result = lab_shell.run(arguments)
    assert result.returncode == 0
    assert result.stdout == "Usage: scripts/lab.sh start|stop|model|sync|setup|web-deps|chat|gateway|status\n"
    assert lab_shell.commands() == []

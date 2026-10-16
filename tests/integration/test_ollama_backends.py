import pytest

from tests.fixtures.lab import LabShell

ARGUMENT_ERROR_EXIT_CODE = 2


def test_docker_backend_starts_without_mac_services_and_reuses_container(lab_shell: LabShell) -> None:
    lab_shell.environment["LAB_OLLAMA_BACKEND"] = "docker"

    started = lab_shell.run(("start",))

    assert started.returncode == 0, started.stderr
    assert (lab_shell.provider_directory / "docker-ollama").is_file()
    assert not (lab_shell.provider_directory / "ollama").exists()
    assert not (lab_shell.provider_directory / "ollama-tunnel").exists()
    assert not any(command[1] == "bootstrap" for command in lab_shell.commands())

    repeated = lab_shell.run(("start",))

    assert repeated.returncode == 0, repeated.stderr
    assert not any("up" in command or "stop" in command or "tar" in command for command in lab_shell.commands())


def test_docker_backend_failure_stops_only_its_created_resources(lab_shell: LabShell) -> None:
    lab_shell.environment["LAB_OLLAMA_BACKEND"] = "docker"
    (lab_shell.provider_directory / "vm-status").write_text("Running")

    result = lab_shell.run(("start",), failures=("up-ollama",))

    assert result.returncode != 0
    assert not (lab_shell.provider_directory / "docker-ollama").exists()
    assert (lab_shell.provider_directory / "vm-status").read_text() == "Running"


def test_backend_change_requires_stopping_mac_and_preserves_existing_services(lab_shell: LabShell) -> None:
    assert lab_shell.run(("start",)).returncode == 0
    model_pid, tunnel_pid = lab_shell.pid("ollama"), lab_shell.pid("ollama-tunnel")
    lab_shell.environment["LAB_OLLAMA_BACKEND"] = "docker"

    result = lab_shell.run(("start",))

    assert result.returncode != 0
    assert "Stop the Mac backend" in result.stderr
    assert (lab_shell.pid("ollama"), lab_shell.pid("ollama-tunnel")) == (model_pid, tunnel_pid)
    assert not (lab_shell.provider_directory / "docker-ollama").exists()


@pytest.mark.parametrize("memory_gib", [3, 8])
def test_docker_model_requires_sufficient_vm_memory(lab_shell: LabShell, memory_gib: int) -> None:
    lab_shell.environment.update(LAB_OLLAMA_BACKEND="docker", LAB_TEST_VM_MEMORY=str(memory_gib * 1024**3))

    result = lab_shell.run(("start",))

    assert result.returncode != 0
    assert "10 GiB VM" in result.stderr
    assert (lab_shell.provider_directory / "vm-status").read_text() == "Stopped"
    assert not (lab_shell.provider_directory / "docker-ollama").exists()


def test_mac_backend_does_not_replace_an_existing_docker_endpoint(lab_shell: LabShell) -> None:
    (lab_shell.provider_directory / "vm-status").write_text("Running")
    (lab_shell.provider_directory / "docker-ollama").write_text("running")

    result = lab_shell.run(("start",))

    assert result.returncode != 0
    assert "port 11434 is already occupied" in result.stderr
    assert (lab_shell.provider_directory / "docker-ollama").read_text() == "running"
    assert (lab_shell.provider_directory / "vm-status").read_text() == "Running"
    assert not (lab_shell.provider_directory / "ollama").exists()
    assert not (lab_shell.provider_directory / "ollama-tunnel").exists()


def test_default_stop_also_removes_the_docker_model(lab_shell: LabShell) -> None:
    lab_shell.environment["LAB_OLLAMA_BACKEND"] = "docker"
    assert lab_shell.run(("start",)).returncode == 0
    lab_shell.environment["LAB_OLLAMA_BACKEND"] = "mac"

    result = lab_shell.run(("stop",))

    assert result.returncode == 0, result.stderr
    assert not (lab_shell.provider_directory / "docker-ollama").exists()
    assert (lab_shell.provider_directory / "vm-status").read_text() == "Stopped"
    lab_shell.environment["LAB_OLLAMA_BACKEND"] = "docker"
    assert lab_shell.run(("stop",)).returncode == 0


def test_model_commands_target_selected_container(lab_shell: LabShell) -> None:
    lab_shell.environment["LAB_OLLAMA_BACKEND"] = "docker"

    result = lab_shell.run(("model",))

    assert result.returncode == 0, result.stderr
    commands = lab_shell.commands()
    assert [command[command.index("exec") :] for command in commands] == [
        ["exec", "-T", "ollama", "ollama", "pull", "qwen3.5:4b"],
        ["exec", "-T", "ollama", "ollama", "create", "agent-lab-qwen:4b", "-f", "/opt/Modelfile"],
    ]


def test_invalid_backend_is_rejected_before_effects(lab_shell: LabShell) -> None:
    lab_shell.environment["LAB_OLLAMA_BACKEND"] = "cloud"

    result = lab_shell.run(("start",))

    assert result.returncode == ARGUMENT_ERROR_EXIT_CODE
    assert "must be mac or docker" in result.stderr
    assert lab_shell.commands() == []

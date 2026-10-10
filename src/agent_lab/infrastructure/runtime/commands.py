from agent_lab.infrastructure.runtime.config import RuntimeConfig


def guest_arguments(config: RuntimeConfig, *arguments: str) -> tuple[str, ...]:
    return ("limactl", "shell", config.vm_name, "--", *arguments)


def compose_arguments(config: RuntimeConfig, *arguments: str) -> tuple[str, ...]:
    return guest_arguments(config, "sudo", "docker", "compose", "-f", config.compose_path, *arguments)

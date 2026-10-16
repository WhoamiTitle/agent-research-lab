from agent_lab.infrastructure.runtime.config import OllamaBackend, RuntimeConfig


def guest_arguments(config: RuntimeConfig, *arguments: str) -> tuple[str, ...]:
    return ("limactl", "shell", config.vm_name, "--", *arguments)


def compose_arguments(config: RuntimeConfig, *arguments: str) -> tuple[str, ...]:
    profile = ("--profile", "docker") if config.ollama_backend == OllamaBackend.DOCKER else ()
    return guest_arguments(config, "sudo", "docker", "compose", "-f", config.compose_path, *profile, *arguments)

import os
import sys
from pathlib import Path

from agent_lab.infrastructure.runtime.config import OllamaBackend, RuntimeConfig
from agent_lab.main.di import init_cli


def main() -> int:
    try:
        environment = {"LAB_OLLAMA_BACKEND": "mac", **os.environ}
        backend = OllamaBackend(environment["LAB_OLLAMA_BACKEND"])
    except ValueError:
        sys.stderr.write("LAB_OLLAMA_BACKEND must be mac or docker.\n")
        return 2
    config = RuntimeConfig(
        project_root=Path(__file__).parents[3],
        home_directory=Path.home(),
        ollama_backend=backend,
    )
    cli = init_cli(config)
    return cli.run(sys.argv[1:])

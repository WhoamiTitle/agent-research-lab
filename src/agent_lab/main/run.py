import sys
from pathlib import Path

from agent_lab.infrastructure.runtime.config import RuntimeConfig
from agent_lab.main.di import init_cli


def main() -> int:
    config = RuntimeConfig(
        project_root=Path(__file__).parents[3],
        home_directory=Path.home(),
    )
    cli = init_cli(config)
    return cli.run(sys.argv[1:])

from agent_lab.application.stand.commands.start_stand import StartStandHandler
from agent_lab.application.stand.commands.stop_stand import StopStandHandler
from agent_lab.application.stand.queries.get_stand_status import GetStandStatusHandler
from agent_lab.infrastructure.process import ProcessRunner
from agent_lab.infrastructure.runtime.config import RuntimeConfig
from agent_lab.infrastructure.runtime.launchd import LaunchdServicesImpl
from agent_lab.infrastructure.runtime.lock import LifecycleLockImpl
from agent_lab.infrastructure.runtime.main import LocalRuntimeImpl
from agent_lab.presentation.cli.main import LabCli


def init_cli(config: RuntimeConfig) -> LabCli:
    runner = ProcessRunner()
    runtime = LocalRuntimeImpl(config, runner, LaunchdServicesImpl(config, runner), LifecycleLockImpl(config))
    return LabCli(StartStandHandler(runtime), StopStandHandler(runtime), GetStandStatusHandler(runtime))

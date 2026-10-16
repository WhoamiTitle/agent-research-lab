from agent_lab.application.deployment.commands.sync_deployment import SyncDeploymentHandler
from agent_lab.application.hermes.commands.chat_with_agent import ChatWithAgentHandler
from agent_lab.application.hermes.commands.install_web_dependencies import InstallWebDependenciesHandler
from agent_lab.application.hermes.commands.setup_agent import SetupAgentHandler
from agent_lab.application.hermes.commands.start_gateway import StartGatewayHandler
from agent_lab.application.model.commands.prepare_model import PrepareModelHandler
from agent_lab.application.stand.commands.start_stand import StartStandHandler
from agent_lab.application.stand.commands.stop_stand import StopStandHandler
from agent_lab.application.stand.components import StandComponent
from agent_lab.application.stand.queries.get_stand_status import GetStandStatusHandler
from agent_lab.infrastructure.deployment.main import DeploymentPreparationImpl
from agent_lab.infrastructure.hermes.main import HermesRuntimeImpl
from agent_lab.infrastructure.model.main import LocalModelImpl
from agent_lab.infrastructure.process import ProcessRunner
from agent_lab.infrastructure.runtime.config import OllamaBackend, RuntimeConfig
from agent_lab.infrastructure.runtime.launchd import LaunchdServicesImpl
from agent_lab.infrastructure.runtime.lock import LifecycleLockImpl
from agent_lab.infrastructure.runtime.main import LocalRuntimeImpl
from agent_lab.presentation.cli.main import CliHandlers, LabCli


def init_cli(config: RuntimeConfig) -> LabCli:
    runner = ProcessRunner()
    runtime = LocalRuntimeImpl(config, runner, LaunchdServicesImpl(config, runner), LifecycleLockImpl(config))
    hermes = HermesRuntimeImpl(config, runner)
    components = (
        (StandComponent.VM, StandComponent.OLLAMA)
        if config.ollama_backend == OllamaBackend.DOCKER
        else tuple(StandComponent)
    )
    handlers = CliHandlers(
        start_stand=StartStandHandler(runtime, components),
        stop_stand=StopStandHandler(runtime),
        get_stand_status=GetStandStatusHandler(runtime),
        prepare_model=PrepareModelHandler(LocalModelImpl(config, runner)),
        sync_deployment=SyncDeploymentHandler(DeploymentPreparationImpl(config, runner)),
        setup_agent=SetupAgentHandler(hermes),
        install_web_dependencies=InstallWebDependenciesHandler(hermes),
        chat_with_agent=ChatWithAgentHandler(hermes),
        start_gateway=StartGatewayHandler(hermes),
    )
    return LabCli(handlers)

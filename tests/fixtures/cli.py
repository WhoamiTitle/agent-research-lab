from agent_lab.application.deployment.commands.sync_deployment import SyncDeploymentHandler
from agent_lab.application.hermes.commands.chat_with_agent import ChatWithAgentHandler
from agent_lab.application.hermes.commands.install_web_dependencies import InstallWebDependenciesHandler
from agent_lab.application.hermes.commands.setup_agent import SetupAgentHandler
from agent_lab.application.hermes.commands.start_gateway import StartGatewayHandler
from agent_lab.application.model.commands.prepare_model import PrepareModelHandler
from agent_lab.application.stand.commands.start_stand import StartStandHandler
from agent_lab.application.stand.commands.stop_stand import StopStandHandler
from agent_lab.application.stand.queries.get_stand_status import GetStandStatusHandler
from agent_lab.presentation.cli.main import CliHandlers, LabCli
from tests.mocks.preparation import PreparationMock
from tests.mocks.runtime import RuntimeMock


def build_cli(runtime: RuntimeMock, preparation: PreparationMock) -> LabCli:
    return LabCli(
        CliHandlers(
            start_stand=StartStandHandler(runtime),
            stop_stand=StopStandHandler(runtime),
            get_stand_status=GetStandStatusHandler(runtime),
            prepare_model=PrepareModelHandler(preparation),
            sync_deployment=SyncDeploymentHandler(preparation),
            setup_agent=SetupAgentHandler(preparation),
            install_web_dependencies=InstallWebDependenciesHandler(preparation),
            chat_with_agent=ChatWithAgentHandler(preparation),
            start_gateway=StartGatewayHandler(preparation),
        )
    )

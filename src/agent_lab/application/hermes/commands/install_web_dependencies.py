from agent_lab.application.hermes.interfaces.runtime import HermesWebDependencies


class InstallWebDependenciesHandler:
    def __init__(self, dependencies: HermesWebDependencies) -> None:
        self._dependencies = dependencies

    def __call__(self) -> None:
        self._dependencies.install_search_dependency()
        self._dependencies.install_browser_dependency()

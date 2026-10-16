from dishka import Provider, Scope, provide

from agent_bot.application.handle_message import HandleMessage


class InteractorProvider(Provider):
    scope = Scope.REQUEST
    handle_message = provide(HandleMessage)

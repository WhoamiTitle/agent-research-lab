import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest

from agent_bot.adapters.hermes.config import HermesConfig
from agent_bot.adapters.hermes.gateway import HermesGatewayImpl
from agent_bot.application.common.agent import AgentApprovalRequiredError, AgentFailedError, AgentTimedOutError

RUN_ID = "run_" + "a" * 32


@asynccontextmanager
async def gateway_client(transport: httpx.MockTransport, *, run_timeout: float = 1) -> AsyncIterator[HermesGatewayImpl]:
    config = HermesConfig(api_key="fixture", poll_interval=0, run_timeout=run_timeout)
    async with httpx.AsyncClient(base_url=config.base_url, transport=transport) as client:
        yield HermesGatewayImpl(config, client)


async def test_run_uses_durable_idempotency_and_conversation_then_returns_output() -> None:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(202, json={"run_id": RUN_ID, "status": "started"})
        return httpx.Response(200, json={"run_id": RUN_ID, "status": "completed", "output": "готов"})

    async with gateway_client(httpx.MockTransport(handle)) as gateway:
        assert await gateway.answer("Контрольный вопрос", request_id="telegram-11") == "готов"

    assert requests[0].headers["Idempotency-Key"] == "telegram-11"
    assert requests[0].headers["X-Hermes-Session-Key"] == "agent-lab-telegram-owner"
    assert requests[0].url.path == "/v1/runs"
    assert requests[1].url.path == f"/v1/runs/{RUN_ID}"
    assert [request.method for request in requests] == ["POST", "GET"]


@pytest.mark.parametrize(
    ("status", "error"),
    [("failed", AgentFailedError), ("waiting_for_approval", AgentApprovalRequiredError)],
)
async def test_failed_or_approval_run_is_stopped(status: str, error: type[Exception]) -> None:
    stopped: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stop"):
            stopped.append(request.url.path)
            return httpx.Response(200, json={"status": "stopping"})
        if request.method == "POST":
            return httpx.Response(202, json={"run_id": RUN_ID})
        return httpx.Response(200, json={"run_id": RUN_ID, "status": status})

    async with gateway_client(httpx.MockTransport(handle)) as gateway:
        with pytest.raises(error):
            await gateway.answer("Контрольный вопрос", request_id="telegram-12")

    assert stopped == [f"/v1/runs/{RUN_ID}/stop"]


async def test_deadline_stops_remote_run() -> None:
    stopped: list[str] = []

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stop"):
            stopped.append(request.url.path)
            return httpx.Response(200)
        if request.method == "POST":
            return httpx.Response(202, json={"run_id": RUN_ID})
        return httpx.Response(200, json={"run_id": RUN_ID, "status": "running"})

    async with gateway_client(httpx.MockTransport(handle), run_timeout=0.02) as gateway:
        with pytest.raises(AgentTimedOutError):
            await gateway.answer("Контрольный вопрос", request_id="telegram-13")

    assert stopped == [f"/v1/runs/{RUN_ID}/stop"]


async def test_cancellation_stops_remote_run_and_propagates() -> None:
    polling = asyncio.Event()
    stopped = asyncio.Event()

    async def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/stop"):
            stopped.set()
            return httpx.Response(200)
        if request.method == "POST":
            return httpx.Response(202, json={"run_id": RUN_ID})
        polling.set()
        await asyncio.Event().wait()
        raise AssertionError("The poll must be cancelled.")

    async with gateway_client(httpx.MockTransport(handle)) as gateway:
        task = asyncio.create_task(gateway.answer("Контрольный вопрос", request_id="telegram-14"))
        await asyncio.wait_for(polling.wait(), timeout=1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert stopped.is_set()

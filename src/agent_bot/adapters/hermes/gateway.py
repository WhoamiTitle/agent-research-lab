import asyncio
import logging
from typing import Annotated

import httpx
from pydantic import BaseModel, Field, ValidationError

from agent_bot.adapters.hermes.config import HermesConfig
from agent_bot.application.common.agent import (
    AgentApprovalRequiredError,
    AgentError,
    AgentFailedError,
    AgentGateway,
    AgentTimedOutError,
    AgentUnavailableError,
)

logger = logging.getLogger(__name__)


class RunAdmission(BaseModel):
    run_id: Annotated[str, Field(pattern=r"^run_[a-f0-9]{32}$")]


class RunStatus(RunAdmission):
    status: str
    output: str | None = None


class HermesGatewayImpl(AgentGateway):
    def __init__(self, config: HermesConfig, client: httpx.AsyncClient) -> None:
        self._config = config
        self._client = client

    async def is_ready(self) -> bool:
        try:
            response = await self._client.get("/health")
        except httpx.HTTPError:
            return False
        else:
            return response.status_code == httpx.codes.OK

    async def answer(self, text: str, *, request_id: str) -> str:
        run_id: str | None = None
        try:
            async with asyncio.timeout(self._config.run_timeout):
                response = await self._client.post(
                    "/v1/runs",
                    headers={"Idempotency-Key": request_id, "X-Hermes-Session-Key": self._config.conversation_key},
                    json={"input": text},
                )
                response.raise_for_status()
                run_id = RunAdmission.model_validate_json(response.content).run_id
                logger.info("hermes_run_admitted")
                return await self._wait_for_result(run_id)
        except asyncio.CancelledError:
            if run_id is not None:
                await asyncio.shield(self._stop(run_id))
            raise
        except TimeoutError:
            if run_id is not None:
                await self._stop(run_id)
            raise AgentTimedOutError from None
        except (httpx.HTTPError, ValidationError):
            if run_id is not None:
                await self._stop(run_id)
            raise AgentUnavailableError from None
        except AgentError:
            if run_id is not None:
                await self._stop(run_id)
            raise

    async def _wait_for_result(self, run_id: str) -> str:
        while True:
            response = await self._client.get(f"/v1/runs/{run_id}")
            response.raise_for_status()
            result = RunStatus.model_validate_json(response.content)
            match result.status:
                case "completed":
                    if result.output and result.output.strip():
                        logger.info("hermes_run_completed")
                        return result.output.strip()
                    raise AgentFailedError
                case "waiting_for_approval":
                    raise AgentApprovalRequiredError
                case "queued" | "started" | "running" | "stopping":
                    await asyncio.sleep(self._config.poll_interval)
                case _:
                    raise AgentFailedError

    async def _stop(self, run_id: str) -> None:
        try:
            async with asyncio.timeout(5):
                response = await self._client.post(f"/v1/runs/{run_id}/stop")
                response.raise_for_status()
        except (httpx.HTTPError, TimeoutError):
            logger.warning("hermes_stop_unconfirmed")

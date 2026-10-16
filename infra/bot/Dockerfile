FROM ghcr.io/astral-sh/uv:0.12.23@sha256:61d393e44e249f2e4b526b6c7ddcecce245946826e608e11c93ad4f5bba55b21 AS uv
FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f

COPY --from=uv /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    TZ=America/Los_Angeles

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src/agent_bot ./src/agent_bot

RUN groupadd --gid 10000 bot && \
    useradd --uid 10000 --gid 10000 --no-create-home bot

USER 10000:10000
ENTRYPOINT ["/app/.venv/bin/python", "-m", "agent_bot"]

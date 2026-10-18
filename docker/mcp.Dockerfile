# DocWiki MCP server image (ACA app "mcp", streamable HTTP on port 8080, Blob-backed releases).
# Built remotely in Azure Container Registry by `azd deploy`; build context = repository root,
# filtered by docker/mcp.Dockerfile.dockerignore. Authentication is done by Container Apps
# built-in auth in front of the container (DOCWIKI_AUTH_MODE=easyauth is set by infra/main.bicep),
# and the server validates the forwarded bearer token again (DOCWIKI_MCP_* token settings).

ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.1

FROM ${UV_IMAGE} AS uv

FROM ${PYTHON_IMAGE} AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN uv venv /opt/venv --python /usr/local/bin/python3.12 \
    && uv pip install --python /opt/venv/bin/python ".[mcp,azure]"

FROM ${PYTHON_IMAGE}
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOCWIKI_MODE=azure \
    HOME=/var/lib/docwiki
RUN useradd --uid 10001 --create-home --home-dir /var/lib/docwiki --shell /usr/sbin/nologin docwiki
COPY --from=build /opt/venv /opt/venv
WORKDIR /var/lib/docwiki
USER 10001
EXPOSE 8080
ENTRYPOINT ["python", "-m", "docwiki.mcp.server", "--http", "0.0.0.0:8080", "--storage", "blob"]

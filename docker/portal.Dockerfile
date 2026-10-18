# DocWiki private portal image (optional ACA app "portal", port 8080): serves the current
# release's site from Blob behind Container Apps built-in auth (Entra sign-in). The app's own
# security headers stay on (its CSP allows 'unsafe-eval' for the Quartz explorer and graph).
# Built remotely in Azure Container Registry by `azd deploy`; build context = repository root,
# filtered by docker/portal.Dockerfile.dockerignore.

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
# Starlette + uvicorn come from the `portal` extra when pyproject.toml declares it, otherwise
# from the `mcp` extra (same web stack).
RUN set -eu; \
    extras="$(python -c 'import tomllib; extras = tomllib.load(open("pyproject.toml", "rb"))["project"].get("optional-dependencies", {}); print("azure,portal" if "portal" in extras else "azure,mcp")')"; \
    uv venv /opt/venv --python /usr/local/bin/python3.12; \
    uv pip install --python /opt/venv/bin/python ".[${extras}]"

FROM ${PYTHON_IMAGE}
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOCWIKI_MODE=azure \
    HOME=/var/lib/docwiki
RUN useradd --uid 10001 --create-home --home-dir /var/lib/docwiki --shell /usr/sbin/nologin docwiki
COPY --from=build /opt/venv /opt/venv
# The site cache (--cache-dir, default .local/portal-cache) lives under the writable home.
WORKDIR /var/lib/docwiki
USER 10001
EXPOSE 8080
ENTRYPOINT ["python", "-m", "docwiki.portal", "--host", "0.0.0.0", "--port", "8080"]

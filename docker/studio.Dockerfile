# DocWiki Studio image (optional ACA app "studio", port 8080): the owner-only web app to upload
# documents, follow the pipeline and ask the Researcher and Librarian agents. Container Apps
# built-in auth (Entra sign-in) sits in front of it and the app checks the signed-in principal
# again (DOCWIKI_STUDIO_ALLOWED_PRINCIPALS); it reaches Blob, the queue and Foundry with its
# managed identity (no key, no secret).
# Built remotely in Azure Container Registry by `azd deploy`; build context = repository root,
# filtered by docker/studio.Dockerfile.dockerignore.

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
# Starlette and uvicorn come from the `portal` extra. The Studio reads the supported file types
# from docwiki.extract, whose package imports Pillow, pypdfium2 and the Office readers when it
# loads: without the `extract` extra the app stops at start-up with ModuleNotFoundError.
RUN uv venv /opt/venv --python /usr/local/bin/python3.12 \
    && uv pip install --python /opt/venv/bin/python ".[azure,portal,extract]"

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
ENTRYPOINT ["python", "-m", "docwiki.studio", "--host", "0.0.0.0", "--port", "8080"]

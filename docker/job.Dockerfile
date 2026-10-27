# DocWiki pipeline job image (ACA jobs "ingest" and "reconcile").
# Built remotely in Azure Container Registry by `azd deploy` (docker.remoteBuild in azure.yaml);
# build context = repository root, filtered by docker/job.Dockerfile.dockerignore.
#   ingest job:    docwiki worker      (image default)
#   reconcile job: docwiki reconcile   (args set by infra/main.bicep and scripts/hooks/postdeploy.py)
#   site stage:    python -m docwiki.site <release> --out <dir> --base-url <url>
# /opt/docwiki mirrors a source checkout: the package is installed in editable mode from
# /opt/docwiki/src next to site/ (Quartz overlay + QUARTZ_VERSION), domains/ and skills/, so the
# engine resolves its domain packs, skill templates, overlay and Quartz cache (.cache/quartz/<tag>)
# there. Quartz is pre-fetched at build time: jobs never clone.
# Base images can be pointed at a mirror (for example an ACR cache rule) with --build-arg.

ARG PYTHON_IMAGE=python:3.12-slim-bookworm
ARG NODE_IMAGE=node:22-bookworm-slim
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.1

FROM ${UV_IMAGE} AS uv

FROM ${NODE_IMAGE} AS node

# Optional folders owned by other lanes (domain packs, skill templates, Quartz overlay) are
# copied through this stage so that the build works whether or not they exist yet.
FROM ${PYTHON_IMAGE} AS context
COPY . /ctx
RUN mkdir -p /ctx/domains /ctx/skills /ctx/site /ctx/evals/results /ctx/docs/assets

FROM ${PYTHON_IMAGE} AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_NO_CACHE=1
WORKDIR /opt/docwiki
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
# Editable install: the package runs from /opt/docwiki/src, so the repository-relative lookups
# (domains/, skills/templates, site/) resolve under /opt/docwiki exactly as in a source checkout.
RUN uv venv /opt/docwiki/.venv --python /usr/local/bin/python3.12 \
    && uv pip install --python /opt/docwiki/.venv/bin/python --editable ".[extract,azure,workflow]" \
    && /opt/docwiki/.venv/bin/python -m compileall -q /opt/docwiki/src

FROM ${PYTHON_IMAGE}
# Fallback Quartz tag, used only when the build context has no site/QUARTZ_VERSION.
ARG QUARTZ_VERSION=v4.5.2
# DOCWIKI_WORK_DIR: local scratch of the runs (raw downloads, release staging), writable by the
# runtime user; storage itself is Blob in azure mode.
ENV PATH=/opt/docwiki/.venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOCWIKI_MODE=azure \
    DOCWIKI_WORK_DIR=/var/lib/docwiki/work \
    HOME=/var/lib/docwiki
RUN set -eu; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates git; \
    rm -rf /var/lib/apt/lists/*; \
    useradd --uid 10001 --create-home --home-dir /var/lib/docwiki --shell /usr/sbin/nologin docwiki; \
    install -d -o 10001 -g 10001 /var/lib/docwiki/work
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
COPY --from=build /opt/docwiki /opt/docwiki
COPY --from=context /ctx/site /opt/docwiki/site
COPY --from=context /ctx/domains /opt/docwiki/domains
COPY --from=context /ctx/skills /opt/docwiki/skills
# The home page's evaluation panel (evals/results/latest.json) and the architecture page's
# diagram (docs/assets/architecture.svg); the site leaves either out when it is missing.
COPY --from=context /ctx/evals/results /opt/docwiki/evals/results
COPY --from=context /ctx/docs/assets /opt/docwiki/docs/assets
# Clone and install the pinned Quartz exactly where docwiki.site looks for it, then hand the
# cache to the runtime user: every site build resets the checkout and writes the overlay into it.
RUN set -eu; \
    if [ ! -s /opt/docwiki/site/QUARTZ_VERSION ]; then \
        printf '%s\n' "$QUARTZ_VERSION" > /opt/docwiki/site/QUARTZ_VERSION; \
    fi; \
    HOME=/root python -c "from docwiki.site.build import default_cache_dir, default_overlay_dir, ensure_quartz, read_quartz_version; print(ensure_quartz(read_quartz_version(default_overlay_dir()), default_cache_dir()))"; \
    test -d /opt/docwiki/.cache/quartz; \
    chown -R 10001:10001 /opt/docwiki/.cache; \
    rm -rf /root/.npm /root/.cache
WORKDIR /opt/docwiki
USER 10001
ENTRYPOINT ["docwiki"]
CMD ["worker"]

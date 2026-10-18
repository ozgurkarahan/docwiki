"""Logging defaults shared by the DocWiki server processes (MCP server, portal)."""

from __future__ import annotations

import logging

__all__ = ["SDK_HTTP_LOGGER", "quiet_sdk_http_logs"]

SDK_HTTP_LOGGER = "azure.core.pipeline.policies.http_logging_policy"
"""Logger of the Azure SDK's per-request HTTP logs (method, URL, headers, body notices)."""


def quiet_sdk_http_logs(level: int | str = logging.INFO) -> None:
    """Keep the Azure SDK's per-request HTTP logs out of logs above ``DEBUG``.

    The SDK logs every request and response at ``INFO``: with ``INFO`` logs, one cold start of
    the MCP server that downloads a release wrote about 100,000 lines to Log Analytics. They are
    kept when the process logs at ``DEBUG``.
    """
    numeric = level if isinstance(level, int) else logging.getLevelName(str(level).upper())
    if not isinstance(numeric, int) or numeric > logging.DEBUG:
        logging.getLogger(SDK_HTTP_LOGGER).setLevel(logging.WARNING)

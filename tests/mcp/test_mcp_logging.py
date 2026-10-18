"""The Azure SDK's per-request HTTP logs stay out of the server logs above DEBUG."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from mcp_testkit import FIXTURE_ROOT

from docwiki.logs import SDK_HTTP_LOGGER, quiet_sdk_http_logs
from docwiki.mcp.server import main


@pytest.fixture(autouse=True)
def _restore_sdk_logger() -> Iterator[None]:
    sdk = logging.getLogger(SDK_HTTP_LOGGER)
    level = sdk.level
    yield
    sdk.setLevel(level)


@pytest.mark.parametrize("level", ["INFO", "WARNING", logging.INFO, "error"])
def test_sdk_http_logs_are_quiet_above_debug(level: int | str) -> None:
    logging.getLogger(SDK_HTTP_LOGGER).setLevel(logging.NOTSET)
    quiet_sdk_http_logs(level)
    assert logging.getLogger(SDK_HTTP_LOGGER).level == logging.WARNING


@pytest.mark.parametrize("level", ["DEBUG", logging.DEBUG])
def test_sdk_http_logs_are_kept_at_debug(level: int | str) -> None:
    logging.getLogger(SDK_HTTP_LOGGER).setLevel(logging.NOTSET)
    quiet_sdk_http_logs(level)
    assert logging.getLogger(SDK_HTTP_LOGGER).level == logging.NOTSET


def test_mcp_main_quiets_sdk_http_logs() -> None:
    # A cold start that downloaded a release logged ~100,000 SDK lines at the default INFO.
    logging.getLogger(SDK_HTTP_LOGGER).setLevel(logging.NOTSET)
    assert main(["--http", "nonsense", "--release", str(FIXTURE_ROOT)]) == 2
    assert logging.getLogger(SDK_HTTP_LOGGER).level == logging.WARNING

"""Optional OpenTelemetry spans and structured logs for the engine (architecture §7).

Spans are created only when a real tracer provider is configured (for example by
``azure-monitor-opentelemetry``); otherwise nothing is imported or recorded. Attributes carry
identifiers and counts only, never document text.
"""

from __future__ import annotations

import contextlib
import logging
import os
from collections.abc import Iterator
from typing import Any

from docwiki import __version__

__all__ = [
    "SPAN_PREFIX",
    "configure_exporter",
    "console_logs",
    "engine_logger",
    "flush_exporter",
    "stage_span",
]

SPAN_PREFIX = "docwiki.stage."
_TYPES = (str, bool, int, float)
engine_logger = logging.getLogger("docwiki.engine")


def configure_exporter() -> bool:
    """Export spans and ``docwiki`` logs to Application Insights when it is configured.

    The jobs get ``APPLICATIONINSIGHTS_CONNECTION_STRING`` from the infrastructure; without an
    exporter their stage and LLM spans and their warnings never reached Application Insights.
    Returns whether the exporter is on. Console output is unchanged (see :func:`console_logs`).
    """
    if not os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
        return False
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor
    except ImportError:
        engine_logger.warning(
            "Application Insights is configured but azure-monitor-opentelemetry is missing"
        )
        return False
    configure_azure_monitor(logger_name="docwiki")
    return True


def console_logs() -> None:
    """Warnings and errors on stderr as bare messages, as Python prints them without handlers.

    An exporter handler on the ``docwiki`` logger would otherwise replace that implicit
    last-resort output; does nothing when the root logger already has handlers.
    """
    logging.basicConfig(level=logging.WARNING, format="%(message)s")


def flush_exporter(timeout_ms: int = 15_000) -> None:
    """Export the spans and logs still buffered (the jobs exit right after their run).

    Relying on the exit hooks lost the last batch: a reconcile run's spans after its debounce
    never reached Application Insights.
    """
    try:
        from opentelemetry import _logs, trace
    except ImportError:
        return
    for provider in (trace.get_tracer_provider(), _logs.get_logger_provider()):
        flush = getattr(provider, "force_flush", None)
        if callable(flush):
            with contextlib.suppress(Exception):
                flush(timeout_ms)


def _tracer() -> Any | None:
    try:
        from opentelemetry import trace
    except ImportError:
        return None
    provider = trace.get_tracer_provider()
    if isinstance(provider, trace.ProxyTracerProvider | trace.NoOpTracerProvider):
        return None
    return provider.get_tracer("docwiki.engine", __version__)


class _Span:
    def __init__(self, span: Any | None) -> None:
        self._span = span

    def set(self, **attributes: Any) -> None:
        if self._span is None:
            return
        self._span.set_attributes(
            {
                f"docwiki.{key}": value
                for key, value in attributes.items()
                if value is not None and isinstance(value, _TYPES)
            }
        )


@contextlib.contextmanager
def stage_span(stage: str, **attributes: Any) -> Iterator[_Span]:
    """``docwiki.stage.<stage>`` span (no-op without a tracer provider)."""
    tracer = _tracer()
    if tracer is None:
        yield _Span(None)
        return
    with tracer.start_as_current_span(SPAN_PREFIX + stage) as span:
        recorder = _Span(span)
        recorder.set(stage=stage, **attributes)
        yield recorder

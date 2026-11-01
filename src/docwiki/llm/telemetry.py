"""Optional OpenTelemetry spans for LLM calls.

``opentelemetry`` is imported lazily and spans are only created when a real tracer provider is
configured (the default proxy/no-op provider means tracing is off). Spans never contain prompt
or document text: only identifiers, token counts, latency and retries.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator, Mapping
from typing import Any

from docwiki import __version__

SPAN_NAME = "docwiki.llm.structured"
EMBED_SPAN_NAME = "docwiki.llm.embed"
_ATTRIBUTE_TYPES = (str, bool, int, float)


class SpanRecorder:
    """Sets attributes on the current LLM span; a no-op when tracing is off."""

    def __init__(self, span: Any | None = None) -> None:
        self._span = span

    @property
    def active(self) -> bool:
        return self._span is not None

    def set_attributes(self, attributes: Mapping[str, Any]) -> None:
        if self._span is None:
            return
        clean = {
            key: value
            for key, value in attributes.items()
            if value is not None and isinstance(value, _ATTRIBUTE_TYPES)
        }
        self._span.set_attributes(clean)


def get_tracer(tracer_provider: Any | None = None) -> Any | None:
    """Tracer from ``tracer_provider`` or the global provider, or ``None`` if tracing is off."""
    try:
        from opentelemetry import trace
    except ImportError:
        return None
    provider = tracer_provider if tracer_provider is not None else trace.get_tracer_provider()
    if isinstance(provider, trace.ProxyTracerProvider | trace.NoOpTracerProvider):
        return None
    return provider.get_tracer("docwiki.llm", __version__)


@contextlib.contextmanager
def llm_span(
    attributes: Mapping[str, Any],
    *,
    tracer_provider: Any | None = None,
    name: str = SPAN_NAME,
) -> Iterator[SpanRecorder]:
    """Context manager wrapping one model call in a ``name`` span (``structured`` by default)."""
    tracer = get_tracer(tracer_provider)
    if tracer is None:
        yield SpanRecorder()
        return
    from opentelemetry.trace import SpanKind

    with tracer.start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        recorder = SpanRecorder(span)
        recorder.set_attributes(attributes)
        yield recorder

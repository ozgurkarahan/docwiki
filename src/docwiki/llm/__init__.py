"""``docwiki.llm``: the only gateway for model calls in DocWiki.

Live calls go to Microsoft Foundry deployments (``fast`` and ``smart`` tiers) through the
Responses API with strict structured outputs and Entra authentication. Tests use
:class:`FakeLlmClient` or :class:`ReplayLlmClient`; every client feeds a :class:`UsageLedger`
whose :meth:`UsageLedger.receipt` is the run's cost receipt. Vectors go through the separate
:class:`EmbeddingClient` protocol (role `embed`). See ``README.md`` in this package.
"""

from docwiki.llm.client import BaseLlmClient, LlmClient
from docwiki.llm.embed_input import (
    EMBED_INPUT_MAX_CHARS,
    EMBED_INPUT_VERSION,
    EmbedInput,
    build_embed_input,
)
from docwiki.llm.embeddings import (
    BaseEmbeddingClient,
    EmbeddingClient,
    EmbeddingInfo,
    EmbeddingResult,
    EmbedPurpose,
    EmbedRequest,
    FakeEmbeddingClient,
    RecordingEmbeddingClient,
    ReplayEmbeddingClient,
    fake_vector,
)
from docwiki.llm.errors import (
    LlmAuthError,
    LlmConfigurationError,
    LlmContentFiltered,
    LlmError,
    LlmFakeHandlerMissing,
    LlmInvalidOutput,
    LlmOutputTruncated,
    LlmRateLimited,
    LlmReplayMissing,
    LlmServiceError,
    LlmTimeout,
)
from docwiki.llm.factory import create_embedding_client, create_llm_client
from docwiki.llm.fake import FakeLlmClient
from docwiki.llm.foundry import FoundryLlmClient
from docwiki.llm.foundry_embeddings import FoundryEmbeddingClient
from docwiki.llm.ledger import (
    CallRecord,
    LlmReceipt,
    PromptUsage,
    ReceiptLine,
    ReceiptTotals,
    UsageLedger,
)
from docwiki.llm.prices import PriceTable, PriceTableInfo, ResolvedPrice
from docwiki.llm.ratelimit import DeploymentRateLimiter, TokenBucket
from docwiki.llm.recording import Recording, RecordingLlmClient, ReplayLlmClient, fixture_path
from docwiki.llm.request import LlmRequest
from docwiki.llm.retry import RetryPolicy, parse_retry_after
from docwiki.llm.schema import StrictSchemaError, to_strict_json_schema
from docwiki.llm.settings import LlmSettings, RateLimit
from docwiki.llm.types import (
    TIERS,
    ContentPart,
    DeploymentInfo,
    ImagePart,
    LlmUsage,
    StructuredResult,
    TextPart,
    Tier,
)

__all__ = [
    "EMBED_INPUT_MAX_CHARS",
    "EMBED_INPUT_VERSION",
    "TIERS",
    "BaseEmbeddingClient",
    "BaseLlmClient",
    "CallRecord",
    "ContentPart",
    "DeploymentInfo",
    "DeploymentRateLimiter",
    "EmbedInput",
    "EmbedPurpose",
    "EmbedRequest",
    "EmbeddingClient",
    "EmbeddingInfo",
    "EmbeddingResult",
    "FakeEmbeddingClient",
    "FakeLlmClient",
    "FoundryEmbeddingClient",
    "FoundryLlmClient",
    "ImagePart",
    "LlmAuthError",
    "LlmClient",
    "LlmConfigurationError",
    "LlmContentFiltered",
    "LlmError",
    "LlmFakeHandlerMissing",
    "LlmInvalidOutput",
    "LlmOutputTruncated",
    "LlmRateLimited",
    "LlmReceipt",
    "LlmReplayMissing",
    "LlmRequest",
    "LlmServiceError",
    "LlmSettings",
    "LlmTimeout",
    "LlmUsage",
    "PriceTable",
    "PriceTableInfo",
    "PromptUsage",
    "RateLimit",
    "ReceiptLine",
    "ReceiptTotals",
    "Recording",
    "RecordingEmbeddingClient",
    "RecordingLlmClient",
    "ReplayEmbeddingClient",
    "ReplayLlmClient",
    "ResolvedPrice",
    "RetryPolicy",
    "StrictSchemaError",
    "StructuredResult",
    "TextPart",
    "Tier",
    "TokenBucket",
    "UsageLedger",
    "build_embed_input",
    "create_embedding_client",
    "create_llm_client",
    "fake_vector",
    "fixture_path",
    "parse_retry_after",
    "to_strict_json_schema",
]

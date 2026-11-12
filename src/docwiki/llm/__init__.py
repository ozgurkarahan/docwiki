"""``docwiki.llm``: the only gateway for model calls in DocWiki.

Live calls go to Microsoft Foundry deployments (``fast`` and ``smart`` tiers) through the
Responses API with strict structured outputs and Entra authentication. Tests use
:class:`FakeLlmClient` or :class:`ReplayLlmClient`; every client feeds a :class:`UsageLedger`
whose :meth:`UsageLedger.receipt` is the run's cost receipt. See ``README.md`` in this package.
"""

from docwiki.llm.client import BaseLlmClient, LlmClient
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
from docwiki.llm.factory import create_llm_client
from docwiki.llm.fake import FakeLlmClient
from docwiki.llm.foundry import FoundryLlmClient
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
    "TIERS",
    "BaseLlmClient",
    "CallRecord",
    "ContentPart",
    "DeploymentInfo",
    "DeploymentRateLimiter",
    "FakeLlmClient",
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
    "RecordingLlmClient",
    "ReplayLlmClient",
    "ResolvedPrice",
    "RetryPolicy",
    "StrictSchemaError",
    "StructuredResult",
    "TextPart",
    "Tier",
    "TokenBucket",
    "UsageLedger",
    "create_llm_client",
    "fixture_path",
    "parse_retry_after",
    "to_strict_json_schema",
]

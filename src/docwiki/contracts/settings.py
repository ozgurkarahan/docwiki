"""Environment settings keys (``DOCWIKI_*``) shared by every lane, with documented defaults."""

from __future__ import annotations

__all__ = ["SETTINGS_DEFAULTS", "SettingsKeys"]


class SettingsKeys:
    """Names of the environment variables (or ``.env`` keys, never committed)."""

    MODE = "DOCWIKI_MODE"  # local | azure
    WORK_DIR = "DOCWIKI_WORK_DIR"  # local folder storage root
    FOUNDRY_PROJECT_ENDPOINT = "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"
    FAST_DEPLOYMENT = "DOCWIKI_FAST_DEPLOYMENT"
    SMART_DEPLOYMENT = "DOCWIKI_SMART_DEPLOYMENT"
    EMBED_DEPLOYMENT = "DOCWIKI_EMBED_DEPLOYMENT"  # embedding deployment (hybrid retrieval)
    EMBED_DIMENSIONS = "DOCWIKI_EMBED_DIMENSIONS"
    EMBED_BATCH_SIZE = "DOCWIKI_EMBED_BATCH_SIZE"  # texts per embedding call
    CONTENT_UNDERSTANDING = "DOCWIKI_CONTENT_UNDERSTANDING"  # true | false
    STORAGE_ACCOUNT = "DOCWIKI_STORAGE_ACCOUNT"
    RAW_CONTAINER = "DOCWIKI_RAW_CONTAINER"
    WORK_CONTAINER = "DOCWIKI_WORK_CONTAINER"
    RELEASES_CONTAINER = "DOCWIKI_RELEASES_CONTAINER"
    QUEUE_NAME = "DOCWIKI_QUEUE_NAME"
    POISON_QUEUE_NAME = "DOCWIKI_POISON_QUEUE_NAME"
    DOMAIN = "DOCWIKI_DOMAIN"
    AUDIENCE = "DOCWIKI_AUDIENCE"
    RELEASE = "DOCWIKI_RELEASE"  # release dir or releases root served by the MCP server
    AUTH_MODE = "DOCWIKI_AUTH_MODE"  # none | easyauth
    ROLE_CLAIM = "DOCWIKI_ROLE_CLAIM"  # claim type(s) carrying app roles (comma-separated)
    READ_ROLE = "DOCWIKI_READ_ROLE"  # app role(s) granting read tools
    OPERATE_ROLE = "DOCWIKI_OPERATE_ROLE"  # app role(s) granting operations tools
    MCP_URL = "DOCWIKI_MCP_URL"  # public MCP endpoint used by the Foundry agents
    AGENT_TIMEOUT_SECONDS = "DOCWIKI_AGENT_TIMEOUT_SECONDS"
    AGENT_MAX_RETRIES = "DOCWIKI_AGENT_MAX_RETRIES"  # SDK retries of agent calls (429, 5xx)
    CANARIES = "DOCWIKI_CANARIES"  # comma-separated injection canaries for the quality gates
    ORCHESTRATOR = "DOCWIKI_ORCHESTRATOR"  # af | async
    SITE_BUILD = "DOCWIKI_SITE_BUILD"  # build the Quartz site during publish (true | false)
    SITE_BASE_URL = "DOCWIKI_SITE_BASE_URL"
    DEBOUNCE_SECONDS = "DOCWIKI_DEBOUNCE_SECONDS"
    LEASE_SECONDS = "DOCWIKI_LEASE_SECONDS"
    RELEASE_RETENTION = "DOCWIKI_RELEASE_RETENTION"
    MAX_PAGES_PER_DOCUMENT = "DOCWIKI_MAX_PAGES_PER_DOCUMENT"
    MAX_TOKENS_PER_RUN = "DOCWIKI_MAX_TOKENS_PER_RUN"
    EXTRACT_CONCURRENCY = "DOCWIKI_EXTRACT_CONCURRENCY"
    LLM_CONCURRENCY = "DOCWIKI_LLM_CONCURRENCY"
    LLM_MAX_RETRIES = "DOCWIKI_LLM_MAX_RETRIES"
    COMPILE_MAP_REDUCE_TOKENS = "DOCWIKI_COMPILE_MAP_REDUCE_TOKENS"
    COMPILE_CHUNK_TOKENS = "DOCWIKI_COMPILE_CHUNK_TOKENS"
    MCP_MAX_CHARS = "DOCWIKI_MCP_MAX_CHARS"
    MCP_POINTER_TTL_SECONDS = "DOCWIKI_MCP_POINTER_TTL_SECONDS"
    MCP_TENANT_ID = "DOCWIKI_MCP_TENANT_ID"  # Entra tenant issuing the MCP API tokens (easyauth)
    MCP_AUDIENCE = "DOCWIKI_MCP_AUDIENCE"  # accepted token audiences (comma-separated)
    MCP_ALLOWED_CLIENT_IDS = "DOCWIKI_MCP_ALLOWED_CLIENT_IDS"  # caller azp/appid allowlist
    MCP_TOKEN_VALIDATION = "DOCWIKI_MCP_TOKEN_VALIDATION"  # required | off (easyauth mode)
    ANSWER_CONTEXT_COVERAGE = "DOCWIKI_ANSWER_CONTEXT_COVERAGE"  # off | on (coverage and gaps)
    RESEARCH_MAX_TOOL_CALLS = "DOCWIKI_RESEARCH_MAX_TOOL_CALLS"
    QUERY_TABLE_MAX_ROWS = "DOCWIKI_QUERY_TABLE_MAX_ROWS"
    DENYLIST = "DOCWIKI_DENYLIST"  # leak-guard deny-list path, outside the repository


SETTINGS_DEFAULTS: dict[str, str] = {
    SettingsKeys.MODE: "local",
    SettingsKeys.WORK_DIR: ".local",
    SettingsKeys.CONTENT_UNDERSTANDING: "false",
    SettingsKeys.RAW_CONTAINER: "raw",
    SettingsKeys.WORK_CONTAINER: "work",
    SettingsKeys.RELEASES_CONTAINER: "releases",
    SettingsKeys.QUEUE_NAME: "ingest",
    SettingsKeys.POISON_QUEUE_NAME: "ingest-poison",
    SettingsKeys.AUDIENCE: "internal",
    SettingsKeys.AUTH_MODE: "none",
    SettingsKeys.ROLE_CLAIM: "roles,http://schemas.microsoft.com/ws/2008/06/identity/claims/role",
    SettingsKeys.READ_ROLE: "Wiki.Read",
    SettingsKeys.OPERATE_ROLE: "Wiki.Operate",
    SettingsKeys.AGENT_TIMEOUT_SECONDS: "300",
    SettingsKeys.DEBOUNCE_SECONDS: "30",
    SettingsKeys.LEASE_SECONDS: "60",
    SettingsKeys.RELEASE_RETENTION: "10",
    SettingsKeys.MAX_PAGES_PER_DOCUMENT: "300",
    SettingsKeys.EXTRACT_CONCURRENCY: "4",
    SettingsKeys.LLM_CONCURRENCY: "6",
    SettingsKeys.LLM_MAX_RETRIES: "3",
    SettingsKeys.EMBED_DIMENSIONS: "512",
    SettingsKeys.EMBED_BATCH_SIZE: "64",
    SettingsKeys.COMPILE_MAP_REDUCE_TOKENS: "24000",
    SettingsKeys.COMPILE_CHUNK_TOKENS: "12000",
    SettingsKeys.MCP_MAX_CHARS: "12000",
    SettingsKeys.MCP_POINTER_TTL_SECONDS: "30",
    SettingsKeys.MCP_TOKEN_VALIDATION: "required",
    SettingsKeys.ANSWER_CONTEXT_COVERAGE: "off",
    SettingsKeys.RESEARCH_MAX_TOOL_CALLS: "12",
    SettingsKeys.QUERY_TABLE_MAX_ROWS: "200",
}
"""Defaults from the spec; keys without a default must be provided when the feature is used."""

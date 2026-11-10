#!/usr/bin/env python3
"""Azure AI Search for the search arms of the knowledge-access study (rag-plus, foundry-iq).

    uv run python scripts/eval_search_index.py provision [--azd-dir DIR]
    uv run python scripts/eval_search_index.py index [--scope full] [--audience public] [--recreate]
    uv run python scripts/eval_search_index.py knowledge [--reasoning-effort low]
    uv run python scripts/eval_search_index.py status [--ps1 FILE]

Every command is idempotent. Settings come from the environment, completed by
``azd env get-values`` of ``--azd-dir`` (default: the repository root) for whatever is missing:
``AZURE_SUBSCRIPTION_ID``, ``AZURE_RESOURCE_GROUP``, ``AZURE_LOCATION``, ``DOCWIKI_RESOURCE_TOKEN``,
``DOCWIKI_FOUNDRY_ACCOUNT_NAME``, ``DOCWIKI_FOUNDRY_PROJECT_ENDPOINT``, ``DOCWIKI_EMBED_*`` and
``DOCWIKI_FAST_*``. Authentication is Entra only (``DefaultAzureCredential``); no key is read.

* ``provision`` creates, if absent, the search service ``srch-docwiki-eval-<resource token>`` in
  the environment's resource group and region: Basic tier (semantic ranker and agentic retrieval;
  managed identity access to models needs Basic or higher), semantic ranker on its standard plan,
  local authentication disabled, a system-assigned identity. It grants the signed-in user Search
  Index Data Contributor and Search Service Contributor on the service, and the service identity
  Cognitive Services OpenAI User and Cognitive Services User on the Foundry account (index
  vectorizer and knowledge base planner).
* ``index`` builds the index of the corpus chunks used by ``baseline-rag`` (local extraction and
  cache of ``evals/run.py``, same scope and audience selection, 800-token chunks), with the
  context header (title, scope, document type, date) embedded with each chunk through
  ``docwiki.llm`` (``DOCWIKI_EMBED_DEPLOYMENT``), and pushes only the chunks that changed.
* ``knowledge`` creates the knowledge source over the index and the knowledge base: planner
  model ``DOCWIKI_FAST_DEPLOYMENT``, retrieval reasoning effort pinned (``low`` by default),
  output mode ``extractiveData`` (no answer synthesis).
* ``status`` prints counts and the variables the runner needs. ``--ps1 FILE`` also writes them as
  PowerShell assignments to a file that must be outside the repository: never commit the values.
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 12):  # noqa: UP036 - must run (and explain) on older interpreters
    major, minor = sys.version_info[:2]
    sys.stderr.write(f"[docwiki] ERROR: Python 3.12+ is required (found {major}.{minor}).\n")
    raise SystemExit(1)

import argparse
import asyncio
import contextlib
import hashlib
import os
import shutil
import subprocess
import time
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from evals.systems import SystemNotConfigured  # noqa: E402
from evals.systems_search import (  # noqa: E402
    DEFAULT_REASONING_EFFORT,
    ENV_ENDPOINT,
    ENV_INDEX,
    ENV_KB,
    KNOWLEDGE_API_VERSION,
    SEARCH_API_VERSION,
    IndexedChunk,
    SearchClient,
    SearchServiceError,
    index_chunks,
    index_definition,
    knowledge_base_definition,
    knowledge_source_definition,
)

ARM = "https://management.azure.com"
ARM_SCOPE = f"{ARM}/.default"
SEARCH_MGMT_API = "2025-05-01"
COGNITIVE_MGMT_API = "2024-10-01"
AUTH_API = "2022-04-01"
DEFAULT_INDEX = "docwiki-eval-chunks"
SERVICE_PREFIX = "srch-docwiki-eval"
UPLOAD_BATCH = 100
USER_ROLES = ("Search Index Data Contributor", "Search Service Contributor")
SERVICE_ROLES = ("Cognitive Services OpenAI User", "Cognitive Services User")
EFFORTS = ("minimal", "low", "medium")


def info(message: str) -> None:
    print(f"[eval-search] {message}", flush=True)


class ScriptError(RuntimeError):
    pass


# ------------------------------------------------------------------------------ settings


def azd_values(directory: Path) -> dict[str, str]:
    """``azd env get-values`` of ``directory`` (empty when azd or the environment is missing)."""
    azd = shutil.which("azd")
    if azd is None:
        return {}
    try:
        output = subprocess.run(
            [azd, "env", "get-values"],
            cwd=directory,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    values: dict[str, str] = {}
    for line in output.splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip().isidentifier():
            values[key.strip()] = value.strip().strip('"')
    return values


@dataclass(frozen=True)
class Settings:
    subscription: str
    resource_group: str
    location: str
    service: str
    endpoint: str
    index: str
    knowledge_source: str
    knowledge_base: str
    foundry_account: str
    embed_deployment: str
    embed_model: str
    embed_dimensions: int
    planner_deployment: str
    planner_model: str
    principal_id: str | None
    principal_type: str

    @property
    def service_id(self) -> str:
        return (
            f"/subscriptions/{self.subscription}/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.Search/searchServices/{self.service}"
        )

    @property
    def foundry_id(self) -> str:
        return (
            f"/subscriptions/{self.subscription}/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.CognitiveServices/accounts/{self.foundry_account}"
        )

    def runner_env(self) -> dict[str, str]:
        return {
            ENV_ENDPOINT: self.endpoint,
            ENV_INDEX: self.index,
            ENV_KB: self.knowledge_base,
        }


def service_name(env: Mapping[str, str]) -> str:
    """``srch-docwiki-eval-<token>``: the environment's resource token, or a hash of the
    subscription and resource group when there is none (3-60 lower-case characters)."""
    token = (env.get("DOCWIKI_RESOURCE_TOKEN") or "").strip().lower()
    if not token:
        seed = f"{env.get('AZURE_SUBSCRIPTION_ID', '')}/{env.get('AZURE_RESOURCE_GROUP', '')}"
        token = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:10]
    token = "".join(char for char in token if char.isalnum())
    return f"{SERVICE_PREFIX}-{token}"[:60].rstrip("-")


def load_settings(args: argparse.Namespace) -> Settings:
    env = {key: value for key, value in os.environ.items() if value.strip()}
    needed = ("AZURE_SUBSCRIPTION_ID", "AZURE_RESOURCE_GROUP", "DOCWIKI_FOUNDRY_ACCOUNT_NAME")
    if any(name not in env for name in needed):
        for key, value in azd_values(args.azd_dir).items():
            env.setdefault(key, value)
    missing = [
        name
        for name in (
            *needed,
            "AZURE_LOCATION",
            "DOCWIKI_EMBED_DEPLOYMENT",
            "DOCWIKI_FAST_DEPLOYMENT",
        )
        if not env.get(name)
    ]
    if missing:
        raise ScriptError(
            f"missing settings: {', '.join(missing)} (load the azd environment or pass --azd-dir)"
        )
    service = (env.get("DOCWIKI_EVAL_SEARCH_SERVICE") or "").strip() or service_name(env)
    index = args.index or env.get(ENV_INDEX) or DEFAULT_INDEX
    return Settings(
        subscription=env["AZURE_SUBSCRIPTION_ID"],
        resource_group=env["AZURE_RESOURCE_GROUP"],
        location=env["AZURE_LOCATION"],
        service=service,
        endpoint=env.get(ENV_ENDPOINT) or f"https://{service}.search.windows.net",
        index=index,
        knowledge_source=f"{index}-ks",
        knowledge_base=env.get(ENV_KB) or f"{index}-kb",
        foundry_account=env["DOCWIKI_FOUNDRY_ACCOUNT_NAME"],
        embed_deployment=env["DOCWIKI_EMBED_DEPLOYMENT"],
        embed_model=env.get("DOCWIKI_EMBED_MODEL") or "text-embedding-3-small",
        embed_dimensions=int(env.get("DOCWIKI_EMBED_DIMENSIONS") or 512),
        planner_deployment=env["DOCWIKI_FAST_DEPLOYMENT"],
        planner_model=env.get("DOCWIKI_FAST_MODEL") or env["DOCWIKI_FAST_DEPLOYMENT"],
        principal_id=env.get("AZURE_PRINCIPAL_ID") or None,
        principal_type=env.get("AZURE_PRINCIPAL_TYPE") or "User",
    )


# ---------------------------------------------------------------------------------- ARM


class Arm:
    """Azure Resource Manager over REST with an Entra token (``DefaultAzureCredential``)."""

    def __init__(self) -> None:
        from azure.identity.aio import DefaultAzureCredential

        self._credential = DefaultAzureCredential()
        self._http = httpx.AsyncClient(base_url=ARM, timeout=120.0)

    async def _headers(self) -> dict[str, str]:
        token = await self._credential.get_token(ARM_SCOPE)
        return {"Authorization": f"Bearer {token.token}"}

    async def call(
        self, method: str, path: str, api: str, body: Any | None = None, **params: str
    ) -> httpx.Response:
        for attempt in range(1, 6):
            response = await self._http.request(
                method,
                path,
                params={"api-version": api, **params},
                json=body,
                headers=await self._headers(),
            )
            if response.status_code not in (429, 503) or attempt == 5:
                return response
            await asyncio.sleep(float(response.headers.get("retry-after") or 2**attempt))
        raise AssertionError("unreachable")  # pragma: no cover

    async def aclose(self) -> None:
        await self._http.aclose()
        await self._credential.close()


def _arm_error(response: httpx.Response, what: str) -> ScriptError:
    try:
        error = response.json().get("error") or {}
    except ValueError:
        error = {}
    return ScriptError(
        f"{what}: HTTP {response.status_code} {error.get('code', '')} {error.get('message', '')}"
    )


async def ensure_service(arm: Arm, settings: Settings) -> dict[str, Any]:
    wanted = {"disableLocalAuth": True, "semanticSearch": "standard"}
    response = await arm.call("GET", settings.service_id, SEARCH_MGMT_API)
    if response.status_code == 404:
        info("creating the search service (Basic, semantic ranker, Entra only, managed identity)")
        body = {
            "location": settings.location,
            "sku": {"name": "basic"},
            "identity": {"type": "SystemAssigned"},
            "tags": {"docwiki-purpose": "eval-knowledge-access"},
            "properties": {
                "replicaCount": 1,
                "partitionCount": 1,
                "hostingMode": "default",
                "publicNetworkAccess": "enabled",
                **wanted,
            },
        }
        response = await arm.call("PUT", settings.service_id, SEARCH_MGMT_API, body)
        if response.status_code not in (200, 201, 202):
            raise _arm_error(response, "create search service")
    elif response.status_code == 200:
        service = response.json()
        props = service.get("properties") or {}
        identity = (service.get("identity") or {}).get("type") or "None"
        drift = {key: value for key, value in wanted.items() if props.get(key) != value}
        if drift or "SystemAssigned" not in identity:
            info("updating the search service (Entra only, semantic ranker, managed identity)")
            patch = {"identity": {"type": "SystemAssigned"}, "properties": wanted}
            response = await arm.call("PATCH", settings.service_id, SEARCH_MGMT_API, patch)
            if response.status_code not in (200, 201, 202):
                raise _arm_error(response, "update search service")
        else:
            info("search service already exists")
    else:
        raise _arm_error(response, "read search service")
    for _ in range(120):
        response = await arm.call("GET", settings.service_id, SEARCH_MGMT_API)
        if response.status_code != 200:
            raise _arm_error(response, "read search service")
        service = response.json()
        props = service.get("properties") or {}
        state = str(props.get("provisioningState") or "").lower()
        if state == "succeeded" and str(props.get("status") or "").lower() == "running":
            return service
        if state == "failed":
            raise ScriptError("the search service provisioning failed")
        await asyncio.sleep(15)
    raise ScriptError("the search service is still provisioning; run provision again later")


async def role_definition(arm: Arm, settings: Settings, role: str) -> str:
    response = await arm.call(
        "GET",
        f"/subscriptions/{settings.subscription}/providers/Microsoft.Authorization/roleDefinitions",
        AUTH_API,
        **{"$filter": f"roleName eq '{role}'"},
    )
    if response.status_code != 200:
        raise _arm_error(response, f"look up role {role}")
    values = response.json().get("value") or []
    if not values:
        raise ScriptError(f"role {role!r} not found")
    return str(values[0]["id"])


async def assign(
    arm: Arm, settings: Settings, scope: str, role: str, principal: str, kind: str
) -> None:
    definition = await role_definition(arm, settings, role)
    name = uuid.uuid5(uuid.NAMESPACE_URL, f"{scope.lower()}|{principal}|{definition.lower()}")
    body = {
        "properties": {
            "roleDefinitionId": definition,
            "principalId": principal,
            "principalType": kind,
        }
    }
    path = f"{scope}/providers/Microsoft.Authorization/roleAssignments/{name}"
    for attempt in range(1, 13):
        response = await arm.call("PUT", path, AUTH_API, body)
        if response.status_code in (200, 201):
            info(f"granted {role} ({kind})")
            return
        code = ""
        with contextlib.suppress(ValueError):
            code = str((response.json().get("error") or {}).get("code") or "")
        if code == "RoleAssignmentExists":
            info(f"{role} ({kind}) already granted")
            return
        if code == "PrincipalNotFound" and attempt < 12:
            await asyncio.sleep(10)  # a new managed identity takes a moment to replicate
            continue
        raise _arm_error(response, f"grant {role}")


def signed_in_user() -> str:
    az = shutil.which("az")
    if az is None:
        raise ScriptError("set AZURE_PRINCIPAL_ID (az CLI not found to look up the signed-in user)")
    result = subprocess.run(
        [az, "ad", "signed-in-user", "show", "--query", "id", "-o", "tsv"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise ScriptError("cannot find the signed-in user: set AZURE_PRINCIPAL_ID")
    return result.stdout.strip()


async def foundry_openai_uri(arm: Arm, settings: Settings) -> str:
    """The Azure OpenAI endpoint of the Foundry account (vectorizer and planner ``resourceUri``)."""
    response = await arm.call("GET", settings.foundry_id, COGNITIVE_MGMT_API)
    if response.status_code != 200:
        raise _arm_error(response, "read Foundry account")
    props = response.json().get("properties") or {}
    endpoints = props.get("endpoints") or {}
    uri = endpoints.get("OpenAI Language Model Instance API")
    if not uri and props.get("customSubDomainName"):
        uri = f"https://{props['customSubDomainName']}.openai.azure.com/"
    if not uri:
        raise ScriptError("the Foundry account has no Azure OpenAI endpoint")
    return str(uri).rstrip("/")


async def provision(settings: Settings) -> None:
    arm = Arm()
    try:
        service = await ensure_service(arm, settings)
        principal = (service.get("identity") or {}).get("principalId")
        if not principal:
            raise ScriptError("the search service has no system-assigned identity")
        user = settings.principal_id or signed_in_user()
        user_type = settings.principal_type
        for role in USER_ROLES:
            await assign(arm, settings, settings.service_id, role, user, user_type)
        for role in SERVICE_ROLES:
            await assign(arm, settings, settings.foundry_id, role, principal, "ServicePrincipal")
    finally:
        await arm.aclose()
    info("provisioned; role assignments can take a few minutes to apply to the data plane")


# --------------------------------------------------------------------------------- index


async def list_index(search: SearchClient, index: str) -> dict[str, str]:
    indexed: dict[str, str] = {}
    skip = 0
    while True:
        _, payload = await search.request(
            "POST",
            f"/indexes/{index}/docs/search",
            operation="list index documents",
            json_body={
                "search": "*",
                "select": "id,chunk_sha256",
                "orderby": "id",
                "top": 1000,
                "skip": skip,
            },
        )
        page = payload.get("value") or []
        indexed.update({str(doc["id"]): str(doc.get("chunk_sha256")) for doc in page})
        if len(page) < 1000:
            return indexed
        skip += len(page)


async def put_index(search: SearchClient, definition: dict[str, Any], recreate: bool) -> None:
    name = definition["name"]
    try:
        await search.request(
            "PUT", f"/indexes/{name}", operation="create index", json_body=definition
        )
    except SearchServiceError as exc:
        if exc.status != 400 or not recreate:
            if exc.status == 400:
                raise ScriptError(
                    f"{exc} (pass --recreate to delete and rebuild the index)"
                ) from None
            raise
        info("deleting the index to rebuild it (--recreate)")
        await search.request("DELETE", f"/indexes/{name}", operation="delete index", ok=(204, 404))
        await search.request(
            "PUT", f"/indexes/{name}", operation="create index", json_body=definition
        )


async def embed(items: Sequence[IndexedChunk]) -> tuple[list[tuple[float, ...]], dict[str, Any]]:
    from docwiki.llm import EMBED_INPUT_VERSION, build_embed_input, create_embedding_client

    client = create_embedding_client()
    try:
        texts = [
            build_embed_input(item.chunk.title, item.section, item.chunk.text).text
            for item in items
        ]
        result = await client.embed(
            texts, "document", EMBED_INPUT_VERSION, metadata={"stage": "eval-search-index"}
        )
        receipt = client.ledger.receipt().model_dump(mode="json")  # type: ignore[attr-defined]
        return list(result.vectors), receipt.get("totals") or {}
    finally:
        await client.aclose()


async def upload(search: SearchClient, index: str, actions: list[dict[str, Any]]) -> None:
    for start in range(0, len(actions), UPLOAD_BATCH):
        batch = actions[start : start + UPLOAD_BATCH]
        _, payload = await search.request(
            "POST",
            f"/indexes/{index}/docs/index",
            operation="index documents",
            json_body={"value": batch},
            ok=(200, 207),
        )
        failed = [item for item in payload.get("value") or [] if not item.get("status")]
        if failed:
            first = failed[0]
            raise ScriptError(
                f"{len(failed)} documents were refused (first: {first.get('statusCode')} "
                f"{first.get('errorMessage')})"
            )


async def build_index(settings: Settings, args: argparse.Namespace) -> None:
    from evals.corpus import load_corpus

    corpus = await load_corpus(args.corpus, cache_dir=args.cache_dir, mode="local")
    items = index_chunks(
        corpus.docs,
        corpus.manifest.select(args.scope, args.audience),
        chunk_tokens=args.chunk_tokens,
    )
    info(f"{len(items)} chunks from {len({item.chunk.path for item in items})} documents")
    arm = Arm()
    try:
        resource_uri = await foundry_openai_uri(arm, settings)
    finally:
        await arm.aclose()
    definition = index_definition(
        settings.index,
        resource_uri=resource_uri,
        embed_deployment=settings.embed_deployment,
        embed_model=settings.embed_model,
        dimensions=settings.embed_dimensions,
    )
    search = SearchClient(settings.endpoint)
    try:
        await put_index(search, definition, args.recreate)
        existing = {} if args.force else await list_index(search, settings.index)
        wanted = {item.id: item for item in items}
        changed = [item for item in items if existing.get(item.id) != item.chunk_sha256]
        stale = sorted(existing.keys() - wanted.keys())
        if args.force:
            stale = sorted((await list_index(search, settings.index)).keys() - wanted.keys())
        actions: list[dict[str, Any]] = []
        if changed:
            vectors, totals = await embed(changed)
            info(
                f"embedded {len(changed)} chunks ({totals.get('input_tokens', 0)} tokens, "
                f"USD {totals.get('estimated_cost_usd')})"
            )
            actions += [
                {"@search.action": "mergeOrUpload", **item.document(vector)}
                for item, vector in zip(changed, vectors, strict=True)
            ]
        actions += [{"@search.action": "delete", "id": doc_id} for doc_id in stale]
        await upload(search, settings.index, actions)
        info(
            f"uploaded {len(changed)}, deleted {len(stale)}, unchanged {len(items) - len(changed)}"
        )
    finally:
        await search.aclose()


async def build_knowledge(settings: Settings, args: argparse.Namespace) -> None:
    arm = Arm()
    try:
        resource_uri = await foundry_openai_uri(arm, settings)
    finally:
        await arm.aclose()
    search = SearchClient(settings.endpoint)
    try:
        await search.request(
            "PUT",
            f"/knowledgesources/{settings.knowledge_source}",
            operation="create knowledge source",
            api_version=KNOWLEDGE_API_VERSION,
            json_body=knowledge_source_definition(settings.knowledge_source, settings.index),
        )
        info("knowledge source ready")
        await search.request(
            "PUT",
            f"/knowledgebases/{settings.knowledge_base}",
            operation="create knowledge base",
            api_version=KNOWLEDGE_API_VERSION,
            json_body=knowledge_base_definition(
                settings.knowledge_base,
                settings.knowledge_source,
                resource_uri=resource_uri,
                deployment=settings.planner_deployment,
                model=settings.planner_model,
                reasoning_effort=args.reasoning_effort,
            ),
        )
        info(
            f"knowledge base ready (planner {settings.planner_model}, reasoning effort "
            f"{args.reasoning_effort}, output extractiveData)"
        )
    finally:
        await search.aclose()


# -------------------------------------------------------------------------------- status


async def status(settings: Settings, args: argparse.Namespace) -> None:
    search = SearchClient(settings.endpoint)
    try:
        try:
            _, count = await search.request(
                "GET", f"/indexes/{settings.index}/docs/$count", operation="count documents"
            )
            info(f"index documents: {count}")
        except SearchServiceError as exc:
            info(f"index: {exc}")
        for kind, name, path in (
            ("knowledge source", settings.knowledge_source, "knowledgesources"),
            ("knowledge base", settings.knowledge_base, "knowledgebases"),
        ):
            try:
                _, definition = await search.request(
                    "GET",
                    f"/{path}/{name}",
                    operation=f"get {kind}",
                    api_version=KNOWLEDGE_API_VERSION,
                )
                effort = (definition.get("retrievalReasoningEffort") or {}).get("kind")
                info(f"{kind}: present" + (f" (reasoning effort {effort})" if effort else ""))
            except SearchServiceError as exc:
                info(f"{kind}: {exc.status} {exc.code or ''}".rstrip())
    finally:
        await search.aclose()
    info(f"API versions: search {SEARCH_API_VERSION}, knowledge {KNOWLEDGE_API_VERSION}")
    print_env(settings, args.ps1)


def print_env(settings: Settings, ps1: Path | None) -> None:
    values = settings.runner_env()
    for key, value in values.items():
        print(f"{key}={value}")
    if ps1 is None:
        return
    target = ps1.resolve()
    if target == REPO_ROOT or REPO_ROOT in target.parents:
        raise ScriptError("--ps1 must point outside the repository (the values are not committed)")
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'$env:{key} = "{value}"' for key, value in values.items()]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    info(f"wrote {len(lines)} variables to the --ps1 file")


# ----------------------------------------------------------------------------------- CLI


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("provision", "index", "knowledge", "status"))
    parser.add_argument("--azd-dir", type=Path, default=REPO_ROOT, help="azd project directory")
    parser.add_argument("--index", help=f"index name (default {ENV_INDEX} or {DEFAULT_INDEX})")
    parser.add_argument("--corpus", type=Path, default=REPO_ROOT / "samples" / "corpus")
    parser.add_argument("--cache-dir", type=Path, default=REPO_ROOT / ".cache" / "evals")
    parser.add_argument("--scope", choices=("full", "all"), default="full")
    parser.add_argument("--audience", default="public")
    parser.add_argument("--chunk-tokens", type=int, default=800)
    parser.add_argument("--recreate", action="store_true", help="rebuild an incompatible index")
    parser.add_argument("--force", action="store_true", help="re-embed and upload every chunk")
    parser.add_argument("--reasoning-effort", choices=EFFORTS, default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--ps1", type=Path, help="also write the runner variables (outside repo)")
    return parser


async def _main(args: argparse.Namespace) -> None:
    settings = load_settings(args)
    if args.command == "provision":
        await provision(settings)
        print_env(settings, args.ps1)
    elif args.command == "index":
        await build_index(settings, args)
    elif args.command == "knowledge":
        await build_knowledge(settings, args)
        print_env(settings, args.ps1)
    else:
        await status(settings, args)


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    started = time.perf_counter()
    try:
        asyncio.run(_main(args))
    except (ScriptError, SearchServiceError, SystemNotConfigured) as exc:
        print(f"[eval-search] ERROR: {exc}", file=sys.stderr)
        return 1
    info(f"done in {time.perf_counter() - started:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

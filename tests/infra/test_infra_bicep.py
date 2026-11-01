"""Static checks of the Bicep templates, parameters and Dockerfiles (plus an optional build)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from infra_testkit import (
    REPO_ROOT,
    STORAGE_BLOB_DATA_CONTRIBUTOR,
    bicep_multiline_var,
    evaluate_condition,
    role_allows,
)

from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.settings import SettingsKeys
from docwiki.llm import settings as llm_settings
from docwiki.orchestration import settings as orchestration_settings
from docwiki.portal.live_ask import ENABLE_ENV, STREAM_PROGRESS_ENV
from docwiki.portal.owner import OWNERS_ENV
from docwiki.site import build as site_build
from docwiki.stages import agentkit

INFRA = REPO_ROOT / "infra"
MAIN = INFRA / "main.bicep"
# The S8 feature switched on by the evaluation MCP app only (enableEvalMcp).
EVAL_FEATURE_ENV = "DOCWIKI_ANSWER_CONTEXT_COVERAGE"
GUID = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
LIST_FUNCTIONS = re.compile(
    r"\blist(Keys|Secrets|Credentials?|ConnectionStrings|AccountSas|ServiceSas|AdminKeys|QueryKeys)\s*\(",
    re.I,
)


def bicep_files() -> list[Path]:
    return sorted(INFRA.rglob("*.bicep"))


def main_text() -> str:
    return MAIN.read_text(encoding="utf-8")


def param_names(text: str) -> set[str]:
    return set(re.findall(r"^param\s+(\w+)\s", text, re.MULTILINE))


def test_targets_subscription_and_allowed_regions() -> None:
    text = main_text()
    assert "targetScope = 'subscription'" in text
    block = re.search(
        r"@allowed\(\[(?P<values>[^\]]*)\]\)\s*@metadata\(\{\s*azd: \{\s*type: 'location'", text
    )
    assert block, "location must be an @allowed azd location parameter"
    regions = re.findall(r"'([a-z0-9]+)'", block.group("values"))
    assert regions == ["swedencentral", "eastus2", "westeurope"]
    assert re.search(r"param location string = 'swedencentral'", text)


def test_spec_parameters_and_defaults() -> None:
    text = main_text()
    expected = {
        "mcpMinReplicas": "0",
        "mcpTokenValidation": "'required'",
        "enablePortal": "false",
        "portalAccess": "'entra'",
        "enableEventTrigger": "true",
        "reconcileCron": "'0 */6 * * *'",
        "audience": "'internal'",
        "domainPack": "'batiment'",
        "enableFoundrySkillsPreview": "false",
        "enableRoutine": "false",
        "deploymentSku": "'GlobalStandard'",
        "embedModel": "'text-embedding-3-small'",
        "embedModelVersion": "'1'",
        "embedCapacity": "50",
        "embedDimensions": "512",
        "budgetContactEmails": "''",
    }
    for name, default in expected.items():
        assert re.search(rf"^param {name} \w+ = {re.escape(default)}$", text, re.MULTILINE), name
    for name in (
        "fastModel",
        "fastModelVersion",
        "fastCapacity",
        "smartModel",
        "smartModelVersion",
        "smartCapacity",
        "budgetAmount",
    ):
        assert name in param_names(text), name
    assert re.search(r"@allowed\(\[\s*'GlobalStandard'\s*'DataZoneStandard'\s*\]\)", text)


def test_parameters_file_maps_existing_parameters() -> None:
    data = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))
    mapped = data["parameters"]
    declared = param_names(main_text())
    assert set(mapped) <= declared
    required = {
        name for name in declared if re.search(rf"^param {name} \w+\s*$", main_text(), re.MULTILINE)
    }
    assert required <= set(mapped), "parameters without default must be mapped"
    assert mapped["budgetContactEmails"]["value"] == "${BUDGET_CONTACT_EMAILS}"
    assert mapped["location"]["value"] == "${AZURE_LOCATION}"
    for name, entry in mapped.items():
        assert re.fullmatch(r"\$\{[A-Z0-9_]+\}", entry["value"]), name


def test_no_key_listing_or_secrets_in_bicep() -> None:
    for path in bicep_files():
        text = path.read_text(encoding="utf-8")
        assert not LIST_FUNCTIONS.search(text), path
        assert "AccountKey=" not in text and "SharedAccessKey" not in text, path
        assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text.replace("@export()", "")), path


def test_every_guid_is_an_allowlisted_public_constant() -> None:
    allowed = {
        line.split("#", 1)[0].strip().lower()
        for line in (REPO_ROOT / "tools" / "leakguard" / "allowed_guids.txt")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.split("#", 1)[0].strip()
    }
    for path in [*bicep_files(), INFRA / "main.parameters.json"]:
        for guid in GUID.findall(path.read_text(encoding="utf-8")):
            assert guid.lower() in allowed, f"{path.name}: {guid} is not in allowed_guids.txt"


def test_zero_secret_resource_settings() -> None:
    storage = (INFRA / "modules" / "storage.bicep").read_text(encoding="utf-8")
    assert "allowSharedKeyAccess: false" in storage
    assert "isVersioningEnabled: true" in storage
    assert "deleteRetentionPolicy" in storage and "containerDeleteRetentionPolicy" in storage
    for name in ("raw", "work", "releases", "ingest", "ingest-poison"):
        assert f"'{name}'" in storage
    assert "deliveryWithResourceIdentity" in storage
    assert "'Microsoft.Storage.BlobCreated'" in storage
    assert "'Microsoft.Storage.BlobDeleted'" in storage
    assert "/blobServices/default/containers/${rawContainerName}/blobs/" in storage
    foundry = (INFRA / "modules" / "foundry.bicep").read_text(encoding="utf-8")
    assert "kind: 'AIServices'" in foundry
    assert "disableLocalAuth: true" in foundry
    assert "allowProjectManagement: true" in foundry
    assert "customSubDomainName: accountName" in foundry
    main = main_text()
    assert "acrAdminUserEnabled: false" in main
    environment = (INFRA / "modules" / "container-apps-environment.bicep").read_text(
        encoding="utf-8"
    )
    assert "destination: 'azure-monitor'" in environment, "no Log Analytics shared key"
    monitoring = (INFRA / "modules" / "monitoring.bicep").read_text(encoding="utf-8")
    assert re.search(r"^param retentionInDays int = 30$", monitoring, re.MULTILINE)


def test_budget_start_date_is_pinned_after_the_first_provision() -> None:
    """Azure refuses to change the start date of an existing budget: a default that follows
    the current month would break every provision in a later month."""
    main = main_text()
    assert re.search(r"^param budgetStartDate string = '\$\{utcNow\('yyyy-MM'\)\}-01'$", main, re.M)
    assert re.search(r"^output DOCWIKI_BUDGET_START_DATE string = budgetStartDate$", main, re.M)
    mapped = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))
    assert mapped["parameters"]["budgetStartDate"]["value"] == "${DOCWIKI_BUDGET_START_DATE}"


def test_embedding_deployment_is_bounded_and_optional() -> None:
    """ADR 0014: a low explicit capacity is the hard bound on embedding spend; 0 = none."""
    foundry = (INFRA / "modules" / "foundry.bicep").read_text(encoding="utf-8")
    block = foundry[foundry.index("resource embedDeployment") :]
    assert "= if (deployEmbed) {" in block.splitlines()[0]
    assert "capacity: embedCapacity" in block
    assert "name: embedModel" in block and "version: embedModelVersion" in block
    assert "versionUpgradeOption: 'OnceCurrentVersionExpired'" in block
    assert re.search(r"^var deployEmbed = embedCapacity > 0$", foundry, re.MULTILINE)
    assert re.search(r"^param embedCapacity int = 0$", foundry, re.MULTILINE)
    main = main_text()
    assert re.search(r"@minValue\(0\)\s*@description\([^\n]*\)\s*param embedCapacity", main)
    assert "var embedTokensPerMinute = embedCapacity * 1000" in main
    assert (
        "var embedRequestsPerMinute = deploymentSku == 'GlobalStandard' ? embedCapacity * 6 "
        ": embedCapacity" in main
    )
    pipeline = main[main.index("var pipelineEnv") : main.index("module ingestJob")]
    embed_env = pipeline[pipeline.index("embedCapacity > 0") :]
    for name in (
        "DOCWIKI_EMBED_DEPLOYMENT",
        "DOCWIKI_EMBED_MODEL",
        "DOCWIKI_EMBED_DIMENSIONS",
        "DOCWIKI_EMBED_TPM",
        "DOCWIKI_EMBED_RPM",
    ):
        assert f"name: '{name}'" in embed_env, name
    # The MCP app gets no embedding setting or role before slice S6.
    mcp = main[main.index("module mcpApp") : main.index("module portalApp")]
    assert "EMBED" not in mcp


def test_job_run_control_matches_the_architecture() -> None:
    job = (INFRA / "modules" / "container-apps-job.bicep").read_text(encoding="utf-8")
    assert "parallelism: 1" in job and "replicaCompletionCount: 1" in job
    assert "maxExecutions: 1" in job
    assert "type: 'azure-queue'" in job
    assert "identity: identityResourceId" in job
    main = main_text()
    ingest = main[main.index("module ingestJob") : main.index("module reconcileJob")]
    assert "pollingIntervalSeconds: 30" in ingest
    assert "replicaTimeoutSeconds: 3600" in ingest
    assert "replicaRetryLimit: 1" in ingest
    assert "['worker']" in ingest
    reconcile = main[main.index("module reconcileJob") : main.index("module mcpApp")]
    assert "triggerType: 'Schedule'" in reconcile
    assert "cronExpression: reconcileCron" in reconcile
    assert "['reconcile']" in reconcile


def test_container_settings_are_known_keys() -> None:
    known = {value for key, value in vars(SettingsKeys).items() if key.isupper()}
    known |= {
        value
        for name, value in vars(llm_settings).items()
        if name.startswith("ENV_") and isinstance(value, str)
    }
    known |= {
        value
        for name, value in vars(llm_settings).items()
        if name.startswith("ENV_") and isinstance(value, dict)
        for value in value.values()
    }
    names = set(re.findall(r"name: '(DOCWIKI_[A-Z0-9_]+)'", main_text()))
    assert names, "no DOCWIKI_* container settings found"
    known.add(ENABLE_ENV)  # the portal's live ask (docwiki.portal.live_ask)
    known.add(STREAM_PROGRESS_ENV)  # its progress steps (docwiki.portal.live_ask)
    known.add(OWNERS_ENV)  # the portal's owners (docwiki.portal.owner, ADR 0009)
    known.add(EVAL_FEATURE_ENV)  # the feature under evaluation (eval MCP app only)
    assert names <= known, f"unknown settings: {sorted(names - known)}"
    for required in (
        "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT",
        "DOCWIKI_FAST_DEPLOYMENT",
        "DOCWIKI_SMART_DEPLOYMENT",
        "DOCWIKI_STORAGE_ACCOUNT",
        "DOCWIKI_AUTH_MODE",
        "DOCWIKI_DOMAIN",
        "DOCWIKI_AUDIENCE",
    ):
        assert required in names
    for other in ("AZURE_CLIENT_ID", "APPLICATIONINSIGHTS_CONNECTION_STRING", "OTEL_SERVICE_NAME"):
        assert f"name: '{other}'" in main_text()
    assert re.search(r"name: 'DOCWIKI_AUTH_MODE'\s*value: 'easyauth'", main_text())


def test_mcp_auth_is_return401_with_audience() -> None:
    main = main_text()
    block = main[main.index("module mcpAuth") : main.index("module mcpConnection")]
    assert "unauthenticatedClientAction: 'Return401'" in block
    # ADR 0003: audience = the application ID URI only (v2 tokens carry the client ID).
    assert re.search(r"allowedAudiences: \[\s*'api://\$\{mcpApiClientId\}'\s*\]", block)
    assert "'/healthz'" in block, "health probe path excluded from built-in auth"
    assert "allowedApplications: mcpAllowedApplications" in block
    auth = (INFRA / "modules" / "app-auth.bicep").read_text(encoding="utf-8")
    assert re.search(r"tokenStore: \{\s*enabled: false", auth)
    assert "clientSecretSettingName" not in auth
    assert "tenant().tenantId}/v2.0'" in auth, "v2 issuer"
    assert re.search(r"defaultAuthorizationPolicy: .*\s*\?\s*null", auth)


def test_mcp_ingress_waits_for_built_in_auth() -> None:
    """Fail closed (portal pattern): external ingress only where the auth config is declared;
    on the first provision the postprovision hook enables it after verifying built-in auth."""
    main = main_text()
    assert re.search(r"^var mcpPublic = !empty\(mcpApiClientId\)$", main, re.MULTILINE)
    assert re.search(
        r"module mcpAuth 'modules/app-auth\.bicep' = if \(!empty\(mcpApiClientId\)\)", main
    )
    block = main[main.index("module mcpApp") : main.index("module portalApp")]
    assert "ingressMode: mcpPublic ? 'external' : 'none'" in block
    assert "ingressMode: 'external'" not in block
    # The agents' endpoint is known before the hook enables the ingress.
    assert (
        "var mcpFqdn = '${names.mcpApp}.${containerAppsEnvironment.outputs.defaultDomain}'" in main
    )
    assert "var mcpUrl = 'https://${mcpFqdn}/mcp'" in main
    assert "mcpApp.outputs.fqdn" not in main
    assert "output DOCWIKI_MCP_FQDN string = mcpFqdn" in main
    module = (INFRA / "modules" / "container-app.bicep").read_text(encoding="utf-8")
    assert "ingress: ingressMode == 'external'" in module and ": null" in module


def test_disabled_portal_is_dormant_at_zero_replicas() -> None:
    """Without ingress or any scale rule the platform keeps each revision's first replica running
    (KEDA has no trigger); a dormant app gets a cron rule that is never active instead."""
    module = (INFRA / "modules" / "container-app.bicep").read_text(encoding="utf-8")
    assert "param dormant bool = false" in module
    rule = module[module.index("var dormantRule") : module.index("resource app ")]
    assert "type: 'cron'" in rule
    assert "start: '0 0 29 2 *'" in rule and "end: '1 0 29 2 *'" in rule
    assert ": dormant ? [dormantRule] : []" in module, "only apps without ingress"
    main = main_text()
    portal = main[main.index("module portalApp") : main.index("module mcpAuth")]
    assert "dormant: !enablePortal" in portal
    # The MCP app (and an enabled portal) keep no rule until the postprovision hook enables
    # ingress: the HTTP default must apply then.
    mcp = main[main.index("module mcpApp") : main.index("module portalApp")]
    assert "dormant:" not in mcp


def test_portal_without_sign_in_only_for_public_audience_builds() -> None:
    """DOCWIKI_PORTAL_ACCESS=public serves the portal without sign-in, and only a public-audience
    build; otherwise the portal gets ingress only once its Entra sign-in is declared."""
    main = main_text()
    assert re.search(
        r"@allowed\(\[\s*'entra'\s*'public'\s*\]\)\s*@description\([^\n]*\)\s*"
        r"param portalAccess string = 'entra'",
        main,
    )
    assert (
        "var portalAnonymous = enablePortal && portalAccess == 'public' && audience == 'public'"
        in main
    )
    assert (
        "var portalPublic = portalAnonymous || (enablePortal && portalAccess == 'entra' && "
        "!empty(portalClientId))" in main
    )
    assert (
        "var portalOwnerSignIn = portalAnonymous && !empty(portalClientId) && "
        "!empty(portalOwners)" in main
    )
    assert (
        "module portalAuth 'modules/app-auth.bicep' = if ((portalPublic && !portalAnonymous) || "
        "portalOwnerSignIn)" in main
    )
    portal = main[main.index("module portalApp") : main.index("module mcpAuth")]
    assert "ingressMode: portalPublic ? 'external' : 'none'" in portal
    assert "output DOCWIKI_PORTAL_ANONYMOUS bool = portalAnonymous" in main
    parameters = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))
    assert parameters["parameters"]["portalAccess"] == {"value": "${DOCWIKI_PORTAL_ACCESS}"}


def test_the_standalone_studio_is_gone() -> None:
    """ADR 0009: the portal is the only web app; no Studio parameter, identity, role, app or
    output is left (teardown still deletes the sign-in registration of an older state)."""
    main = main_text()
    assert "studio" not in main.lower()
    for module in ("storage.bicep", "foundry.bicep"):
        text = (INFRA / "modules" / module).read_text(encoding="utf-8")
        assert "studio" not in text.lower(), module
    mapped = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))["parameters"]
    assert not [name for name, entry in mapped.items() if "studio" in f"{name} {entry}".lower()]
    outputs = re.findall(r"^output (\w+) ", main, re.MULTILINE)
    assert len(outputs) <= 64, "ARM caps a template at 64 outputs (Bicep rule max-outputs)"


def _resource(text: str, name: str) -> str:
    """The declaration of ``resource <name>`` in a Bicep file (up to its closing brace)."""
    return text[text.index(f"resource {name} ") :].split("\n}\n", 1)[0]


def test_the_owner_upload_role_never_deletes() -> None:
    """The portal's raw/ role for the owner's uploads (ADR 0009) withholds the delete only: soft
    delete and versioning keep what a replacement overwrites."""
    storage = (INFRA / "modules" / "storage.bicep").read_text(encoding="utf-8")
    condition = bicep_multiline_var(storage, "noDeleteCondition")
    delete = (
        "!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})"
    )
    assert delete in condition
    assert condition.count("ActionMatches") == 1, "only the delete is withheld from the role"
    upload = {"path": "uploads/a.pdf", "container": "raw"}
    for action in ("blobs/read", "blobs/write", "blobs/add/action"):
        assert evaluate_condition(condition, action, **upload), action
        assert role_allows(STORAGE_BLOB_DATA_CONTRIBUTOR, action, condition=condition, **upload)
    assert not evaluate_condition(condition, "blobs/delete", **upload)
    assert not role_allows(
        STORAGE_BLOB_DATA_CONTRIBUTOR, "blobs/delete", condition=condition, **upload
    )
    assert "principalType: 'ServicePrincipal'" in _resource(storage, "portalRawUploader")
    roles = (INFRA / "modules" / "roles.bicep").read_text(encoding="utf-8")
    assert "storageQueueDataReader: '19e7f393-937e-4f77-808e-94535e297925'" in roles
    header = storage[: storage.index("import {")]
    assert "the portal" in header and "Studio" not in header, "the header lists the identities"


INBOX = StorageKeys.INBOX_QUERIES.removeprefix(StorageKeys.WORK + "/") + "/"
"""The answers inbox as a blob path of the ``work`` container (``inbox/queries/``)."""


def test_mcp_server_validates_the_forwarded_token() -> None:
    main = main_text()
    block = main[main.index("module mcpApp") : main.index("module portalApp")]
    expected = {
        "DOCWIKI_AUTH_MODE": "'easyauth'",
        "DOCWIKI_MCP_TENANT_ID": "tenant().tenantId",
        "DOCWIKI_MCP_TOKEN_VALIDATION": "mcpTokenValidation",
        "DOCWIKI_MCP_AUDIENCE": "'api://${mcpApiClientId},${mcpApiClientId}'",
        "DOCWIKI_MCP_ALLOWED_CLIENT_IDS": "join(mcpAllowedApplications, ',')",
    }
    for name, value in expected.items():
        assert re.search(rf"name: '{name}'\s*value: {re.escape(value)}", block), name
    # Unset until known (the server refuses to start without an audience).
    assert re.search(r"mcpPublic\s*\?\s*\[\s*\{\s*name: 'DOCWIKI_MCP_AUDIENCE'", block)
    assert re.search(r"empty\(mcpAllowedApplications\)\s*\?\s*\[\]", block)
    assert re.search(
        r"@allowed\(\[\s*'required'\s*'off'\s*\]\)\s*@description\([^\n]*\)\s*"
        r"param mcpTokenValidation string = 'required'",
        main,
    )
    mapped = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))
    assert mapped["parameters"]["mcpTokenValidation"]["value"] == "${DOCWIKI_MCP_TOKEN_VALIDATION}"
    assert mapped["parameters"]["mcpAllowedClientIds"]["value"] == (
        "${DOCWIKI_MCP_ALLOWED_CLIENT_IDS}"
    )


def test_mcp_connection_uses_the_agents_own_identities() -> None:
    main = main_text()
    assert re.search(
        r"module mcpConnection 'modules/mcp-connection\.bicep' = if \(!empty\(mcpApiClientId\)\)",
        main,
    )
    block = main[main.index("module mcpConnection") : main.index("module portalAuth")]
    assert "audience: 'api://${mcpApiClientId}'" in block
    assert "mcpUrl: mcpUrl" in block and "connectionName: mcpConnectionName" in block
    module = (INFRA / "modules" / "mcp-connection.bicep").read_text(encoding="utf-8")
    assert "connections@2025-10-01-preview'" in module, "AgenticIdentityToken needs a preview API"
    assert "category: 'RemoteTool'" in module and "authType: 'AgenticIdentityToken'" in module
    assert "project-per-agent" not in main and "ProjectManagedIdentity" not in module


def test_each_workload_runs_as_its_own_identity() -> None:
    main = main_text()
    for module in ("identity", "mcpIdentity", "portalIdentity"):
        assert (
            f"module {module} 'br/public:avm/res/managed-identity/user-assigned-identity:" in main
        )
    blocks = {
        "ingest": main[main.index("module ingestJob") : main.index("module reconcileJob")],
        "reconcile": main[main.index("module reconcileJob") : main.index("module mcpApp")],
        "mcp": main[main.index("module mcpApp") : main.index("module portalApp")],
        "portal": main[main.index("module portalApp") : main.index("module mcpAuth")],
    }
    expected = {
        "ingest": "identity",
        "reconcile": "identity",
        "mcp": "mcpIdentity",
        "portal": "portalIdentity",
    }
    for workload, module in expected.items():
        block = blocks[workload]
        assert f"identityResourceId: {module}.outputs.resourceId" in block, workload
    for workload in ("mcp", "portal"):
        module = expected[workload]
        assert re.search(
            rf"name: 'AZURE_CLIENT_ID'\s*value: {module}\.outputs\.clientId", blocks[workload]
        ), workload
    pipeline = main[main.index("var pipelineEnv") : main.index("module ingestJob")]
    assert re.search(r"name: 'AZURE_CLIENT_ID'\s*value: identity\.outputs\.clientId", pipeline)
    assert "healthPath" not in blocks["mcp"], "/healthz answers 503 before the first release"
    registry = main[main.index("module registry") : main.index("module storage")]
    for module in set(expected.values()):
        assert f"principalId: {module}.outputs.principalId" in registry, module
    # Every identity pulls its image and publishes its telemetry.
    assert len(re.findall(r"roleDefinitionIdOrName: 'AcrPull'", registry)) == len(
        set(expected.values())
    )
    monitoring = main[main.index("module monitoring") : main.index("module registry")]
    for module in set(expected.values()):
        assert f"{module}.outputs.principalId" in monitoring, module


def test_mcp_probes_tolerate_cold_starts() -> None:
    """Explicit TCP probes: /healthz answers 503 before the first release (no HTTP probes); the
    startup probe allows about two minutes without probing every second."""
    main = main_text()
    mcp = main[main.index("module mcpApp") : main.index("module portalApp")]
    assert "tcpProbes: true" in mcp and "healthPath" not in mcp
    module = (INFRA / "modules" / "container-app.bicep").read_text(encoding="utf-8")
    assert "param tcpProbes bool = false" in module
    assert "var probes = !empty(healthPath) ? httpProbes : tcpProbes ? tcpProbeSet : []" in module
    block = module[module.index("var tcpProbeSet") : module.index("var probes =")]
    assert "httpGet" not in block
    probes = re.findall(r"type: '(\w+)'\s*tcpSocket: \{\s*port: targetPort\s*\}", block)
    assert probes == ["Startup", "Liveness", "Readiness"]
    startup = block[: block.index("type: 'Liveness'")]
    values = {
        key: int(value)
        for key, value in re.findall(
            r"(initialDelaySeconds|periodSeconds|failureThreshold): (\d+)", startup
        )
    }
    assert values["failureThreshold"] <= 10, "the API caps failureThreshold at 10"
    assert 1 <= values["initialDelaySeconds"] <= 60
    budget = values["initialDelaySeconds"] + values["periodSeconds"] * values["failureThreshold"]
    assert 110 <= budget <= 130, budget
    assert values["periodSeconds"] > 1, "fewer failed attempts logged than the platform default"


def test_jobs_queue_roles_allow_visibility_renewal() -> None:
    storage = (INFRA / "modules" / "storage.bicep").read_text(encoding="utf-8")
    jobs = storage[storage.index("// Jobs identity") : storage.index("// MCP app identity")]
    assigned = re.findall(
        r"resource (runtime\w+) '[^']+' = \{\s*scope: (\w+)\s*"
        r"name: guid\(\w+\.id, runtimePrincipalId, roleIds\.(\w+)\)",
        jobs,
    )
    queues = {(scope, role) for _, scope, role in assigned if scope.endswith("Queue")}
    # Update Message (visibility renewal) needs queues/messages/write: only Queue Data Contributor
    # has it among the built-in roles; the poison queue only receives copies (Put Message).
    assert queues == {
        ("ingestQueue", "storageQueueDataContributor"),
        ("poisonQueue", "storageQueueDataMessageSender"),
    }


def test_mcp_storage_access_is_least_privilege() -> None:
    storage = (INFRA / "modules" / "storage.bicep").read_text(encoding="utf-8")
    assert "runtimeIngestSender" not in storage, "the jobs never enqueue on ingest"
    condition = storage[
        storage.index("var mcpWorkWriteCondition") : storage.index("resource storage ")
    ]
    # Writes are limited to what the MCP server writes (docwiki.contracts.layout).
    for key in (StorageKeys.REPORTS_DIR + "/", StorageKeys.PROPOSALS_DIR + "/"):
        assert f"StringStartsWith '{key.removeprefix('work/')}'" in condition, key
    assert f"StringEquals '{StorageKeys.OVERLAY.removeprefix('work/')}'" in condition
    for action in ("blobs/write", "blobs/add/action", "blobs/delete", "blobs/move/action"):
        assert f"blobServices/containers/{action}'" in condition, action
    work = storage[
        storage.index("resource mcpWorkScopedContributor") : storage.index(
            "resource mcpIngestSender"
        )
    ]
    assert "condition: mcpWorkWriteCondition" in work and "conditionVersion: '2.0'" in work
    mcp_scopes = re.findall(
        r"resource mcp\w+ '[^']+' = \{\s*scope: (\w+)", storage[storage.index("var mcpWork") :]
    )
    assert sorted(mcp_scopes) == ["ingestQueue", "releasesContainer", "workContainer"]
    portal_scopes = re.findall(r"resource portal\w+ '[^']+' = \{\s*scope: (\w+)", storage)
    assert portal_scopes == ["releasesContainer", "workContainer", "ingestQueue"]


def test_portal_storage_access_is_least_privilege() -> None:
    """ADR 0009: the portal reads releases/, raw/ and work/ and peeks the queue; only with the
    owner's uploads may it write raw/, and never delete there."""
    storage = (INFRA / "modules" / "storage.bicep").read_text(encoding="utf-8")
    reader = storage[storage.index("resource portalRawReader") :]
    reader = reader[: reader.index("\n}\n")]
    assert "= if (!portalUploads)" in reader and "storageBlobDataReader" in reader
    uploader = storage[storage.index("resource portalRawUploader") :]
    uploader = uploader[: uploader.index("\n}\n")]
    assert "= if (portalUploads)" in uploader
    assert "condition: noDeleteCondition" in uploader and "conditionVersion: '2.0'" in uploader
    work = storage[storage.index("resource portalWorkReader") :]
    work = work[: work.index("\n}\n")]
    assert "storageBlobDataReader" in work
    queue = storage[storage.index("resource portalIngestReader") :]
    queue = queue[: queue.index("\n}\n")]
    assert "storageQueueDataReader" in queue
    portal = storage[storage.index("// Portal identity") : storage.index("// Deployer (operator)")]
    # Slice C: the owner's rebuild sends to the ingest queue, only with the owner's sign-in.
    sender = storage[storage.index("resource portalIngestSender") :]
    sender = sender[: sender.index("\n}\n")]
    assert "= if (portalUploads)" in sender and "scope: ingestQueue" in sender
    assert portal.count("MessageSender") == 2  # the sender's role id (in a multi-line call)
    assert "Owner" not in portal.replace("owner", "")
    main = main_text()
    assert "portalUploads: portalOwnerSignIn" in main
    auth = main[main.index("module portalAuth") : main.index("module budget ")]
    assert "unauthenticatedClientAction: portalOwnerSignIn ? 'AllowAnonymous'" in auth
    # Built-in auth refuses every browser POST that carries its session cookie: the public ask
    # must be excluded, the owner's routes must not be.
    assert "'/api/ask'" in auth and "/api/owner" not in auth
    portal_app = main[main.index("module portalApp") : main.index("module mcpAuth")]
    assert "name: 'DOCWIKI_PORTAL_OWNERS'" in portal_app
    owners = portal_app[portal_app.index("portalOwnerSignIn\n") :]
    assert owners.index("? [") < owners.index("DOCWIKI_PORTAL_OWNERS")


def test_event_grid_sender_role_is_on_the_account() -> None:
    # Event Grid validates managed-identity delivery to a queue at the storage account scope.
    storage = (INFRA / "modules" / "storage.bicep").read_text(encoding="utf-8")
    block = storage[storage.index("resource eventGridQueueSender") :]
    assert re.match(r"resource eventGridQueueSender '[^']+' = \{\s*scope: storage\s", block)


def test_storage_network_perimeter_is_opt_in() -> None:
    main = main_text()
    assert re.search(r"^param networkPerimeter bool = false$", main, re.MULTILINE)
    assert re.search(r"^param allowedIpRanges string = ''$", main, re.MULTILINE)
    storage = (INFRA / "modules" / "storage.bicep").read_text(encoding="utf-8")
    assert "publicNetworkAccess: networkPerimeter ? 'SecuredByPerimeter' : 'Enabled'" in storage
    # Event Grid's destination checks carry no subscription identity: no subscription inside.
    assert re.findall(
        r"^resource (\w+) 'Microsoft\.EventGrid/systemTopics/eventSubscriptions@[^']+' = (.+) \{$",
        storage,
        re.MULTILINE,
    ) == [("rawToIngest", "if (!networkPerimeter)"), ("inboxToIngest", "if (!networkPerimeter)")]
    perimeter = (INFRA / "modules" / "network-perimeter.bicep").read_text(encoding="utf-8")
    assert "accessMode: 'Enforced'" in perimeter
    assert "direction: 'Inbound'" in perimeter and "id: subscription().id" in perimeter
    assert "addressPrefixes: allowedAddressPrefixes" in perimeter
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", perimeter), "no literal addresses"


def test_dockerfiles_are_non_root_with_expected_entrypoints() -> None:
    expected = {
        "job.Dockerfile": ('ENTRYPOINT ["docwiki"]', 'CMD ["worker"]'),
        "mcp.Dockerfile": (
            'ENTRYPOINT ["python", "-m", "docwiki.mcp.server", "--http", "0.0.0.0:8080", '
            '"--storage", "blob"]',
        ),
        "portal.Dockerfile": (
            'ENTRYPOINT ["python", "-m", "docwiki.portal", "--host", "0.0.0.0", "--port", "8080"]',
        ),
    }
    for name, lines in expected.items():
        text = (REPO_ROOT / "docker" / name).read_text(encoding="utf-8")
        assert re.search(r"^USER 10001$", text, re.MULTILINE), name
        assert "ARG PYTHON_IMAGE=python:3.12-slim" in text, name
        assert not re.search(r"^ADD\s", text, re.MULTILINE), name
        for line in lines:
            assert line in text, (name, line)


def test_dockerfile_extras_exist() -> None:
    import tomllib

    extras = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "optional-dependencies"
    ]
    for name in ("job.Dockerfile", "mcp.Dockerfile"):
        text = (REPO_ROOT / "docker" / name).read_text(encoding="utf-8")
        used = re.findall(r'"\.\[([a-z,]+)\]"', text)
        assert used, name
        for group in used:
            assert set(group.split(",")) <= set(extras), (name, group)
    portal = (REPO_ROOT / "docker" / "portal.Dockerfile").read_text(encoding="utf-8")
    assert '"azure,portal" if "portal" in extras else "azure,mcp"' in portal
    assert {"azure", "mcp"} <= set(extras), "portal web stack fallback"


def test_job_image_mirrors_a_checkout_for_the_site_stage() -> None:
    job = (REPO_ROOT / "docker" / "job.Dockerfile").read_text(encoding="utf-8")
    assert "ARG NODE_IMAGE=node:22" in job
    assert re.search(r"apt-get install -y --no-install-recommends ca-certificates git", job)
    assert "WORKDIR /opt/docwiki" in job
    assert '--editable ".[extract,azure,workflow]"' in job, "package runs from /opt/docwiki/src"
    assert "COPY --from=build /opt/docwiki /opt/docwiki" in job
    for folder in ("site", "domains", "skills"):
        assert f"COPY --from=context /ctx/{folder} /opt/docwiki/{folder}" in job, folder
    assert "ensure_quartz(read_quartz_version(default_overlay_dir()), default_cache_dir())" in job
    assert "chown -R 10001:10001 /opt/docwiki/.cache" in job
    assert "ARG QUARTZ_VERSION=" in job and "/opt/docwiki/site/QUARTZ_VERSION" in job
    # Run scratch (raw downloads, release staging) must be writable by the runtime user.
    assert "DOCWIKI_WORK_DIR=/var/lib/docwiki/work" in job
    assert "install -d -o 10001 -g 10001 /var/lib/docwiki/work" in job


def test_engine_resolves_the_image_layout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With the editable install, repository-relative lookups land under /opt/docwiki."""
    root = tmp_path / "opt" / "docwiki"
    (root / "site").mkdir(parents=True)
    (root / "site" / "QUARTZ_VERSION").write_text("v4.5.2\n", encoding="utf-8")
    (root / "skills" / "templates").mkdir(parents=True)
    (root / "domains" / "batiment").mkdir(parents=True)
    package = root / "src" / "docwiki"
    for module, name in ((site_build, "site/build.py"), (agentkit, "stages/agentkit.py")):
        path = package / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        monkeypatch.setattr(module, "__file__", str(path))
    settings_file = package / "orchestration" / "settings.py"
    settings_file.parent.mkdir(parents=True)
    settings_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(orchestration_settings, "__file__", str(settings_file))
    monkeypatch.chdir(tmp_path)
    assert site_build.default_overlay_dir() == (root / "site").resolve()
    assert site_build.default_cache_dir() == (root / ".cache" / "quartz").resolve()
    assert site_build.read_quartz_version(site_build.default_overlay_dir()) == "v4.5.2"
    assert agentkit.default_templates_dir() == (root / "skills" / "templates").resolve()
    assert (
        orchestration_settings.resolve_pack_path("batiment")
        == (root / "domains" / "batiment").resolve()
    )


# ---------------------------------------------------------------------------
# Optional: compile with the Bicep CLI when it is installed (no Azure access needed;
# the Azure Verified Modules are restored from the public registry).
# ---------------------------------------------------------------------------


def _bicep_command() -> list[str] | None:
    """Build command prefix: the Bicep CLI takes the file positionally, az needs --file."""
    if os.environ.get("DOCWIKI_SKIP_BICEP_BUILD"):
        return None
    if shutil.which("bicep"):
        return ["bicep", "build"]
    az = shutil.which("az")
    if not az:
        return None
    probe = subprocess.run([az, "bicep", "version"], capture_output=True, text=True, check=False)
    return [az, "bicep", "build", "--file"] if probe.returncode == 0 else None


@pytest.fixture(scope="module")
def compiled(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    command = _bicep_command()
    if command is None:
        pytest.skip("Bicep CLI not installed (set DOCWIKI_SKIP_BICEP_BUILD to skip explicitly)")
    out = tmp_path_factory.mktemp("bicep") / "main.json"
    result = subprocess.run(
        [*command, str(MAIN), "--outfile", str(out)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    diagnostics = [
        line for line in result.stderr.splitlines() if re.search(r"(Error|Warning) ", line)
    ]
    assert result.returncode == 0, result.stderr
    assert not diagnostics, "\n".join(diagnostics)
    return json.loads(out.read_text(encoding="utf-8"))


def test_bicep_build_is_clean(compiled: dict[str, Any]) -> None:
    text = json.dumps(compiled)
    assert not LIST_FUNCTIONS.search(text), "the compiled template must not call list*()"
    outputs = compiled["outputs"]
    for name in (
        "AZURE_CONTAINER_REGISTRY_ENDPOINT",
        "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT",
        "DOCWIKI_STORAGE_ACCOUNT",
        "DOCWIKI_MCP_URL",
        "DOCWIKI_INGEST_JOB_NAME",
        "DOCWIKI_RECONCILE_JOB_NAME",
        "DOCWIKI_MCP_IDENTITY_CLIENT_ID",
        "DOCWIKI_PORTAL_IDENTITY_CLIENT_ID",
        "DOCWIKI_MCP_CONNECTION",
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
    ):
        assert name in outputs, name
    assert len(outputs) <= 64, "ARM caps a template at 64 outputs"


def _values(resources: Any) -> list[dict[str, Any]]:
    return list(resources.values() if isinstance(resources, dict) else resources)


def test_compiled_inbox_trigger(compiled: dict[str, Any]) -> None:
    (storage,) = [
        resource
        for resource in _values(compiled["resources"])
        if resource["type"] == "Microsoft.Resources/deployments" and resource["name"] == "storage"
    ]
    template = storage["properties"]["template"]
    nested = _values(template["resources"])
    (inbox,) = [item for item in nested if "inbox-to-ingest" in json.dumps(item.get("name"))]
    (raw,) = [item for item in nested if "raw-to-ingest" in json.dumps(item.get("name"))]
    assert inbox["type"] == "Microsoft.EventGrid/systemTopics/eventSubscriptions"
    assert inbox["condition"] == raw["condition"] == "[not(parameters('networkPerimeter'))]"
    assert inbox["properties"]["filter"]["includedEventTypes"] == ["Microsoft.Storage.BlobCreated"]
    assert inbox["properties"]["filter"]["subjectBeginsWith"] == (
        "[format('/blobServices/default/containers/{0}/blobs/" + INBOX + "', "
        "variables('workContainerName'))]"
    )
    for key in ("deliveryWithResourceIdentity", "retryPolicy", "eventDeliverySchema"):
        assert inbox["properties"][key] == raw["properties"][key], key
    # No custom role is left: the Studio's inbox writer went with the Studio (ADR 0009).
    assert not [
        item for item in nested if item["type"] == "Microsoft.Authorization/roleDefinitions"
    ]


def test_live_ask_is_optional_and_only_the_portal_gets_its_settings() -> None:
    """ADR 0008: the gateway URL is a parameter (never created or committed); off by default."""
    main = main_text()
    assert re.search(r"^param enableLiveAsk bool = false$", main, re.MULTILINE)
    assert re.search(r"^param liveAskEndpoint string = ''$", main, re.MULTILINE)
    assert "var liveAskEnabled = enablePortal && enableLiveAsk && !empty(liveAskEndpoint)" in main
    env = main[main.index("var liveAskEnv") : main.index("module portalApp")]
    assert "name: 'DOCWIKI_LIVE_ASK'" in env and "value: '1'" in env
    assert "name: 'DOCWIKI_FOUNDRY_PROJECT_ENDPOINT'" in env and "value: liveAskEndpoint" in env
    portal = main[main.index("module portalApp") : main.index("module mcpAuth")]
    assert "liveAskEnv" in portal and "value: portalIdentity.outputs.clientId" in portal
    assert main.count("liveAskEnv") == 2  # declared once, used by the portal only
    parameters = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))
    assert parameters["parameters"]["enableLiveAsk"] == {"value": "${DOCWIKI_ENABLE_LIVE_ASK}"}
    assert parameters["parameters"]["liveAskEndpoint"] == {"value": "${DOCWIKI_LIVE_ASK_ENDPOINT}"}


def test_live_ask_policy_is_a_template_with_the_documented_limits() -> None:
    import xml.etree.ElementTree as ET

    text = (INFRA / "apim" / "docwiki-live-ask-policy.xml").read_text(encoding="utf-8")
    root = ET.fromstring(text)
    assert set(re.findall(r"\{\{(\w+)\}\}", text)) == {
        "TENANT_ID",
        "PORTAL_CLIENT_ID",
        "FOUNDRY_ACCOUNT_URL",
    }
    inbound = root.find("inbound")
    assert inbound is not None
    token = inbound.find("validate-azure-ad-token")
    assert token is not None and token.get("tenant-id") == "{{TENANT_ID}}"
    assert [a.text for a in token.iter("audience")] == ["https://ai.azure.com"]
    assert [a.text for a in token.iter("application-id")] == ["{{PORTAL_CLIENT_ID}}"]
    questions = [
        (item.tag, item.attrib)
        for when in inbound.iter("when")
        for item in when
        if item.tag in ("rate-limit-by-key", "llm-token-limit")
    ]
    assert [tag for tag, _ in questions] == [
        "rate-limit-by-key",
        "llm-token-limit",
        "llm-token-limit",
    ]
    rate, per_visitor, overall = (attrs for _, attrs in questions)
    assert (rate["calls"], rate["renewal-period"]) == ("3", "300")  # v2 tiers: at most 300 s
    assert (per_visitor["tokens-per-minute"], per_visitor["token-quota"]) == ("20000", "60000")
    assert per_visitor["token-quota-period"] == "Daily"
    assert (overall["counter-key"], overall["token-quota"]) == ("docwiki-global", "1500000")
    assert overall["token-quota-period"] == "Daily"
    assert all("POST" in (when.get("condition") or "") for when in inbound.iter("when"))
    # Order: limits, visitor header removed, then the gateway's own identity and the backend.
    tags = [child.tag for child in inbound]
    assert (
        tags.index("choose")
        < tags.index("set-header")
        < tags.index("authentication-managed-identity")
    )
    assert tags[-1] == "set-backend-service"
    assert inbound.find("authentication-managed-identity").get("resource") == "https://ai.azure.com"  # type: ignore[union-attr]
    assert inbound.find("set-backend-service").get("base-url") == "{{FOUNDRY_ACCOUNT_URL}}"  # type: ignore[union-attr]
    assert root.find(".//llm-emit-token-metric") is not None
    assert not GUID.search(text) and "azure-api.net" not in text


def test_portal_custom_domain_and_warm_replica_are_optional() -> None:
    """A custom domain set by hand would be dropped by the next provision: Bicep declares it and
    only references the managed certificate (issued once outside Bicep), so the binding stays."""
    main = main_text()
    assert re.search(r"^param portalCustomDomain string = ''$", main, re.MULTILINE)
    assert re.search(r"^param portalCertificateName string = ''$", main, re.MULTILINE)
    assert re.search(
        r"@minValue\(0\)\s*@maxValue\(1\)\s*@description\([^\n]*\)\s*"
        r"param portalMinReplicas int = 0",
        main,
    )
    domains = main[main.index("var portalCustomDomains") : main.index("var mcpPublic")]
    assert "empty(portalCustomDomain)" in domains and "bindingType: 'Disabled'" in domains
    assert "bindingType: 'SniEnabled'" in domains
    assert "'Microsoft.App/managedEnvironments/managedCertificates'" in domains
    assert "resource " not in domains, "the certificate is referenced, never created"
    portal = main[main.index("module portalApp") : main.index("module mcpAuth")]
    assert "customDomains: portalCustomDomains" in portal
    assert "minReplicas: enablePortal ? portalMinReplicas : 0" in portal
    assert main.count("customDomains:") == 1, "only the portal gets a custom domain"
    module = (INFRA / "modules" / "container-app.bicep").read_text(encoding="utf-8")
    assert "param customDomains array = []" in module
    ingress = module[module.index("ingress: ingressMode == 'external'") : module.index(": null")]
    assert "customDomains: customDomains" in ingress
    mapped = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))["parameters"]
    assert mapped["portalCustomDomain"] == {"value": "${DOCWIKI_PORTAL_CUSTOM_DOMAIN}"}
    assert mapped["portalCertificateName"] == {"value": "${DOCWIKI_PORTAL_CERTIFICATE_NAME}"}
    assert mapped["portalMinReplicas"] == {"value": "${DOCWIKI_PORTAL_MIN_REPLICAS}"}


def test_compiled_portal_custom_domain(compiled: dict[str, Any]) -> None:
    expression = compiled["variables"]["portalCustomDomains"]
    assert "parameters('portalCustomDomain')" in expression
    assert "parameters('portalCertificateName')" in expression
    assert "Microsoft.App/managedEnvironments/managedCertificates" in expression
    modules = {
        resource["name"]: resource
        for resource in _values(compiled["resources"])
        if resource["type"] == "Microsoft.Resources/deployments"
    }
    portal = modules["portalApp"]["properties"]["parameters"]
    assert portal["customDomains"] == {"value": "[variables('portalCustomDomains')]"}
    assert portal["maxReplicas"] == {"value": 1}
    assert "customDomains" not in modules["mcpApp"]["properties"]["parameters"]


# ---------------------------------------------------------------------------
# Optional evaluation environment (enableEvalMcp, off by default; S7)
# ---------------------------------------------------------------------------


def _eval_blocks(main: str) -> dict[str, str]:
    return {
        "app": main[main.index("module mcpEvalApp") : main.index("module mcpEvalAuth")],
        "auth": main[main.index("module mcpEvalAuth") : main.index("module mcpEvalConnection")],
        "connection": main[main.index("module mcpEvalConnection") : main.index("// Outputs")],
    }


def _env(block: str) -> dict[str, str]:
    return dict(re.findall(r"name: '([A-Z0-9_]+)'\s*value: ([^\n]+)", block))


def _settings(block: str, *keys: str) -> dict[str, str]:
    return {
        key: match.group(1)
        for key in keys
        if (match := re.search(rf"^\s*{key}: ([^\n]+)$", block, re.MULTILINE))
    }


def test_eval_mcp_is_off_by_default_and_needs_the_production_auth() -> None:
    main = main_text()
    assert re.search(r"^param enableEvalMcp bool = false$", main, re.MULTILINE)
    assert re.search(r"^param evalMcpAllowedClientIds string = ''$", main, re.MULTILINE)
    assert "var evalMcpEnabled = enableEvalMcp && mcpPublic" in main
    mapped = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))["parameters"]
    assert mapped["enableEvalMcp"] == {"value": "${DOCWIKI_ENABLE_EVAL_MCP}"}
    assert mapped["evalMcpAllowedClientIds"] == {"value": "${DOCWIKI_EVAL_MCP_ALLOWED_CLIENT_IDS}"}
    for module in ("mcpEvalApp", "mcpEvalAuth", "mcpEvalConnection"):
        assert re.search(rf"^module {module} '[^']+' = if \(evalMcpEnabled\) \{{", main, re.M)
    # Production is untouched: nothing outside the evaluation section names it.
    production = main[: main.index("// Evaluation environment")]
    assert "evalMcp" not in production.replace("param enableEvalMcp", "").replace(
        "param evalMcpAllowedClientIds", ""
    )
    assert "mcpEvalApp: 'ca-mcp-eval-${resourceToken}'" in main
    assert "var evalMcpConnectionName = '${take(mcpConnectionName, 28)}-eval'" in main
    assert "output DOCWIKI_EVAL_MCP_URL string = evalMcpEnabled ? evalMcpUrl : ''" in main
    assert (
        "output DOCWIKI_EVAL_MCP_CONNECTION string = evalMcpEnabled ? evalMcpConnectionName : ''"
        in main
    )


def test_eval_mcp_app_mirrors_production_with_the_feature_on() -> None:
    main = main_text()
    prod = main[main.index("module mcpApp") : main.index("// The live ask needs")]
    app = _eval_blocks(main)["app"]
    assert EVAL_FEATURE_ENV not in prod, "production keeps the feature off"
    same = (
        "containerName",
        "environmentId",
        "workloadProfileName",
        "identityResourceId",
        "registryServer",
        "image",
        "cpu",
        "memory",
        "maxReplicas",
        "targetPort",
        "tcpProbes",
    )
    assert _settings(app, *same) == _settings(prod, *same)
    assert len(_settings(app, *same)) == len(same)
    assert "    name: names.mcpEvalApp\n" in app
    assert _settings(app, "minReplicas", "ingressMode", "tags") == {
        "minReplicas": "0",
        "ingressMode": "'external'",
        "tags": "tags",
    }, "zero replicas at rest; no azd service tag (azd deploy updates production only)"
    prod_env, eval_env = _env(prod), _env(app)
    assert eval_env.pop(EVAL_FEATURE_ENV) == "'on'"
    assert eval_env.pop("OTEL_SERVICE_NAME") == "'docwiki-mcp-eval'"
    assert prod_env.pop("OTEL_SERVICE_NAME") == "'docwiki-mcp'"
    assert eval_env.pop("DOCWIKI_MCP_ALLOWED_CLIENT_IDS") == "join(evalMcpAllowedApplications, ',')"
    prod_env.pop("DOCWIKI_MCP_ALLOWED_CLIENT_IDS")
    assert eval_env == prod_env, "same identity, release, tenant, audience and token validation"
    assert re.search(r"env: concat\(\s*sharedEnv,", app), "same storage and release settings"
    allowed = main[main.index("var evalMcpAllowedApplications") : main.index("module mcpEvalApp")]
    assert "union(\n  mcpAllowedApplications," in allowed, "the production agents stay allowed"


def test_eval_mcp_auth_and_connection_mirror_production() -> None:
    main = main_text()
    blocks = _eval_blocks(main)
    auth_block = main[main.index("module mcpAuth") : main.index("module mcpConnection")]
    prod_connection = main[main.index("module mcpConnection") : main.index("// Entra sign-in")]
    keys = ("clientId", "unauthenticatedClientAction")
    assert _settings(blocks["auth"], *keys) == _settings(auth_block, *keys)
    for fragment in ("allowedAudiences: [\n      'api://${mcpApiClientId}'\n    ]", "'/healthz'"):
        assert fragment in auth_block and fragment in blocks["auth"], fragment
    assert "containerAppName: names.mcpEvalApp" in blocks["auth"]
    assert "allowedApplications: evalMcpAllowedApplications" in blocks["auth"]
    keys = ("accountName", "projectName", "audience")
    assert _settings(blocks["connection"], *keys) == _settings(prod_connection, *keys)
    assert _settings(blocks["connection"], "connectionName", "mcpUrl") == {
        "connectionName": "evalMcpConnectionName",
        "mcpUrl": "evalMcpUrl",
    }
    assert (
        "var evalMcpUrl = 'https://${names.mcpEvalApp}.${containerAppsEnvironment.outputs"
        ".defaultDomain}/mcp'" in main
    )


def test_compiled_eval_mcp_is_conditional(compiled: dict[str, Any]) -> None:
    assert compiled["parameters"]["enableEvalMcp"]["defaultValue"] is False
    assert compiled["variables"]["evalMcpEnabled"] == (
        "[and(parameters('enableEvalMcp'), variables('mcpPublic'))]"
    )
    modules = {
        resource["name"]: resource
        for resource in _values(compiled["resources"])
        if resource["type"] == "Microsoft.Resources/deployments"
    }
    for name in ("mcpEvalApp", "mcpEvalAuth", "mcpEvalConnection"):
        assert modules[name]["condition"] == "[variables('evalMcpEnabled')]", name
    for name in ("mcpApp", "mcpAuth", "mcpConnection"):
        text = json.dumps(modules[name]["properties"]["parameters"])
        assert "evalMcp" not in text and "mcpEval" not in text, name
    prod = modules["mcpApp"]["properties"]["parameters"]
    app = modules["mcpEvalApp"]["properties"]["parameters"]
    for key in ("image", "identityResourceId", "registryServer", "environmentId", "cpu", "memory"):
        assert app[key] == prod[key], key
    assert app["minReplicas"] == {"value": 0}
    outputs = compiled["outputs"]
    for name in ("DOCWIKI_EVAL_MCP_URL", "DOCWIKI_EVAL_MCP_CONNECTION"):
        assert outputs[name]["value"].startswith("[if(variables('evalMcpEnabled'), "), name
        assert outputs[name]["value"].endswith(", '')]"), name

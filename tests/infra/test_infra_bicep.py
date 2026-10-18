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
from infra_testkit import REPO_ROOT

from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.settings import SettingsKeys
from docwiki.llm import settings as llm_settings
from docwiki.orchestration import settings as orchestration_settings
from docwiki.site import build as site_build
from docwiki.stages import agentkit

INFRA = REPO_ROOT / "infra"
MAIN = INFRA / "main.bicep"
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
        "enableStudio": "false",
        "studioMinReplicas": "1",
        "enableEventTrigger": "true",
        "reconcileCron": "'0 */6 * * *'",
        "audience": "'internal'",
        "domainPack": "'wind-om'",
        "enableFoundrySkillsPreview": "false",
        "enableRoutine": "false",
        "deploymentSku": "'GlobalStandard'",
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
    # The Studio reads its own settings (docwiki.studio.config), not the engine's.
    studio_config = pytest.importorskip("docwiki.studio.config")
    known |= {
        value
        for name, value in vars(studio_config).items()
        if name.endswith("_ENV") and isinstance(value, str)
    }
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
        "module portalAuth 'modules/app-auth.bicep' = if (portalPublic && !portalAnonymous)" in main
    )
    portal = main[main.index("module portalApp") : main.index("module mcpAuth")]
    assert "ingressMode: portalPublic ? 'external' : 'none'" in portal
    assert "output DOCWIKI_PORTAL_ANONYMOUS bool = portalAnonymous" in main
    parameters = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))
    assert parameters["parameters"]["portalAccess"] == {"value": "${DOCWIKI_PORTAL_ACCESS}"}


def test_studio_parameters_outputs_and_mapping() -> None:
    main = main_text()
    for declaration in (
        r"^param enableStudio bool = false$",
        r"^param studioClientId string = ''$",
        r"^param studioAllowedPrincipals string = ''$",
        r"^param studioMinReplicas int = 1$",
        r"^param studioImage string = ''$",
        r"^param studioExists bool = false$",
    ):
        assert re.search(declaration, main, re.MULTILINE), declaration
    assert re.search(
        r"@minValue\(0\)\s*@maxValue\(1\)\s*@description\([^\n]*\)\s*param studioMinReplicas int",
        main,
    ), "one replica at most: questions in flight live in memory"
    assert "studioIdentity: 'id-docwiki-studio-${resourceToken}'" in main
    assert "studioApp: 'ca-studio-${resourceToken}'" in main
    mapped = json.loads((INFRA / "main.parameters.json").read_text(encoding="utf-8"))["parameters"]
    assert {name: entry["value"] for name, entry in mapped.items() if "studio" in name.lower()} == {
        "enableStudio": "${DOCWIKI_ENABLE_STUDIO}",
        "studioMinReplicas": "${DOCWIKI_STUDIO_MIN_REPLICAS}",
        "studioClientId": "${DOCWIKI_STUDIO_CLIENT_ID}",
        "studioAllowedPrincipals": "${DOCWIKI_STUDIO_ALLOWED_PRINCIPALS}",
        "studioImage": "${SERVICE_STUDIO_IMAGE_NAME}",
        "studioExists": "${SERVICE_STUDIO_RESOURCE_EXISTS}",
    }
    outputs = re.findall(r"^output (\w+) ", main, re.MULTILINE)
    for name in (
        "DOCWIKI_STUDIO_IDENTITY_NAME",
        "DOCWIKI_STUDIO_IDENTITY_CLIENT_ID",
        "DOCWIKI_STUDIO_IDENTITY_PRINCIPAL_ID",
        "DOCWIKI_STUDIO_APP_NAME",
        "DOCWIKI_ENABLE_STUDIO",
        "DOCWIKI_STUDIO_URL",
    ):
        assert name in outputs, name
    assert "output DOCWIKI_ENABLE_STUDIO bool = enableStudio" in main
    assert (
        "var studioUrl = 'https://${names.studioApp}.${containerAppsEnvironment.outputs.defaultDomain}'"
        in main
    )
    assert "output DOCWIKI_STUDIO_URL string = enableStudio ? studioUrl : ''" in main
    assert len(outputs) <= 64, "ARM caps a template at 64 outputs (Bicep rule max-outputs)"


def test_studio_ingress_waits_for_sign_in_and_an_allowed_owner() -> None:
    """Fail closed (portal pattern): external ingress only where the Entra sign-in and an allowed
    owner are declared; on the first provision the postprovision hook declares both, verifies the
    built-in auth and only then enables ingress."""
    main = main_text()
    assert re.search(
        r"^var studioPublic = enableStudio && !empty\(studioClientId\) && "
        r"!empty\(studioAllowedPrincipals\)$",
        main,
        re.MULTILINE,
    )
    assert "module studioAuth 'modules/app-auth.bicep' = if (studioPublic)" in main
    block = main[main.index("module studioApp") : main.index("module studioAuth")]
    assert "ingressMode: studioPublic ? 'external' : 'none'" in block
    assert "ingressMode: 'external'" not in block
    auth = main[main.index("module studioAuth") : main.index("module budget")]
    assert "clientId: studioClientId" in auth
    assert re.search(r"allowedAudiences: \[\s*studioClientId\s*\]", auth)
    assert "unauthenticatedClientAction: 'RedirectToLoginPage'" in auth
    assert re.search(r"excludedPaths: \[\s*'/healthz'\s*'/livez'\s*\]", auth)
    assert "allowedApplications" not in auth
    # The new modules come after the portal's and before the budget: the other tests slice
    # main.bicep between module names.
    order = [main.index(f"module {name} ") for name in ("portalAuth", "studioApp", "studioAuth")]
    assert order == sorted(order) and order[-1] < main.index("module budget ")


def test_studio_app_settings_and_scale() -> None:
    main = main_text()
    block = main[main.index("module studioApp") : main.index("module studioAuth")]
    assert "'azd-service-name': 'studio'" in block and "containerName: 'studio'" in block
    assert "image: !empty(resolvedStudioImage) ? resolvedStudioImage : placeholderAppImage" in block
    assert "module studioCurrentImage 'modules/current-image.bicep'" in main
    assert (
        "var resolvedStudioImage = !empty(studioImage) ? studioImage : "
        "studioCurrentImage.outputs.image" in main
    )
    # The names are the app's own (test_container_settings_are_known_keys checks they exist).
    expected = {
        "AZURE_CLIENT_ID": "studioIdentity.outputs.clientId",
        "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": "foundry.outputs.projectEndpoint",
        "DOCWIKI_STUDIO_REQUIRE_SIGN_IN": "'true'",
        "DOCWIKI_STUDIO_ALLOWED_PRINCIPALS": "studioAllowedPrincipals",
        "DOCWIKI_STUDIO_WIKI_URL": "portalUrl",
        "OTEL_SERVICE_NAME": "'docwiki-studio'",
    }
    for name, value in expected.items():
        assert re.search(rf"name: '{name}'\s*value: {re.escape(value)}", block), name
    assert re.search(r"concat\(\s*sharedEnv,", block), "the shared storage settings"
    # Unset until known: the app refuses everyone without an allowed owner.
    assert re.search(r"empty\(studioAllowedPrincipals\)\s*\?\s*\[\]", block)
    # The wiki link only exists with a portal.
    assert re.search(r"enablePortal\s*\?\s*\[\s*\{\s*name: 'DOCWIKI_STUDIO_WIKI_URL'", block)
    assert "cpu: '0.5'" in block and "memory: '1Gi'" in block
    assert "minReplicas: enableStudio ? studioMinReplicas : 0" in block
    assert "maxReplicas: 1" in block, "questions and approvals in flight live in one replica"
    assert "dormant: !enableStudio" in block
    assert "targetPort: 8080" in block and "tcpProbes: true" in block


def test_studio_storage_access_is_least_privilege() -> None:
    storage = (INFRA / "modules" / "storage.bicep").read_text(encoding="utf-8")
    assert re.search(r"^param studioPrincipalId string = ''$", storage, re.MULTILINE)
    assert "var grantStudio = !empty(studioPrincipalId)" in storage
    assert re.findall(r"^resource (studio\w+) ", storage, re.MULTILINE) == [
        "studioRawContributor",
        "studioWorkReader",
        "studioReleasesReader",
        "studioIngestReader",
    ]
    assigned = re.findall(
        r"^resource (studio\w+) '[^']+' = if \(grantStudio\) \{\s*scope: (\w+)\s*"
        r"name: guid\(\w+\.id, studioPrincipalId, roleIds\.(\w+)\)",
        storage,
        re.MULTILINE,
    )
    # Uploads to raw/, reads work/ (source states, run reports) and releases/ (pointer, catalog),
    # peeks the ingest queue: nothing else, and nothing without a Studio identity.
    assert assigned == [
        ("studioRawContributor", "rawContainer", "storageBlobDataContributor"),
        ("studioWorkReader", "workContainer", "storageBlobDataReader"),
        ("studioReleasesReader", "releasesContainer", "storageBlobDataReader"),
        ("studioIngestReader", "ingestQueue", "storageQueueDataReader"),
    ]
    condition = storage[
        storage.index("var studioRawCondition") : storage.index("resource storage ")
    ]
    delete = (
        "!(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})"
    )
    assert delete in condition
    assert condition.count("ActionMatches") == 1, "only the delete is withheld from the role"
    raw = storage[
        storage.index("resource studioRawContributor") : storage.index("resource studioWorkReader")
    ]
    assert "condition: studioRawCondition" in raw and "conditionVersion: '2.0'" in raw
    assert "principalType: 'ServicePrincipal'" in raw
    for name in ("studioWorkReader", "studioReleasesReader", "studioIngestReader"):
        block = storage[storage.index(f"resource {name} ") :].split("\n}\n", 1)[0]
        assert "condition:" not in block, name
    roles = (INFRA / "modules" / "roles.bicep").read_text(encoding="utf-8")
    assert "storageQueueDataReader: '19e7f393-937e-4f77-808e-94535e297925'" in roles
    assert "Studio" in storage[: storage.index("import {")], "the header lists the identities"


def test_studio_foundry_access_is_azure_ai_user_only() -> None:
    foundry = (INFRA / "modules" / "foundry.bicep").read_text(encoding="utf-8")
    assert re.search(r"^param studioPrincipalId string = ''$", foundry, re.MULTILINE)
    assert "var grantStudio = !empty(studioPrincipalId)" in foundry
    assert re.findall(
        r"^resource (studio\w+) '[^']+' = if \(grantStudio\) \{\s*scope: (\w+)\s*"
        r"name: guid\(\w+\.id, studioPrincipalId, roleIds\.(\w+)\)",
        foundry,
        re.MULTILINE,
    ) == [("studioAzureAiUser", "account", "azureAiUser")]
    assert len(re.findall(r"^resource studio\w+ ", foundry, re.MULTILINE)) == 1
    # While the Studio is disabled its identity holds no data-plane role.
    main = main_text()
    for module, following in (("storage", "foundry"), ("foundry", "containerAppsEnvironment")):
        block = main[main.index(f"module {module} ") : main.index(f"module {following} ")]
        assert "studioPrincipalId: enableStudio ? studioIdentity.outputs.principalId : ''" in block


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
    for module in ("identity", "mcpIdentity", "portalIdentity", "studioIdentity"):
        assert (
            f"module {module} 'br/public:avm/res/managed-identity/user-assigned-identity:" in main
        )
    blocks = {
        "ingest": main[main.index("module ingestJob") : main.index("module reconcileJob")],
        "reconcile": main[main.index("module reconcileJob") : main.index("module mcpApp")],
        "mcp": main[main.index("module mcpApp") : main.index("module portalApp")],
        "portal": main[main.index("module portalApp") : main.index("module mcpAuth")],
        "studio": main[main.index("module studioApp") : main.index("module studioAuth")],
    }
    expected = {
        "ingest": "identity",
        "reconcile": "identity",
        "mcp": "mcpIdentity",
        "portal": "portalIdentity",
        "studio": "studioIdentity",
    }
    for workload, module in expected.items():
        block = blocks[workload]
        assert f"identityResourceId: {module}.outputs.resourceId" in block, workload
    for workload in ("mcp", "portal", "studio"):
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
    assert portal_scopes == ["releasesContainer"]


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
    assert re.search(r"resource rawToIngest '[^']+' = if \(!networkPerimeter\)", storage)
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
        "studio.Dockerfile": (
            'ENTRYPOINT ["python", "-m", "docwiki.studio", "--host", "0.0.0.0", "--port", "8080"]',
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
    for name in ("job.Dockerfile", "mcp.Dockerfile", "studio.Dockerfile"):
        text = (REPO_ROOT / "docker" / name).read_text(encoding="utf-8")
        used = re.findall(r'"\.\[([a-z,]+)\]"', text)
        assert used, name
        for group in used:
            assert set(group.split(",")) <= set(extras), (name, group)
    portal = (REPO_ROOT / "docker" / "portal.Dockerfile").read_text(encoding="utf-8")
    assert '"azure,portal" if "portal" in extras else "azure,mcp"' in portal
    assert {"azure", "mcp"} <= set(extras), "portal web stack fallback"
    # The Studio needs the web stack, the Azure SDKs and, because docwiki.studio imports
    # docwiki.extract (whose package imports Pillow and the document readers), `extract`.
    studio = (REPO_ROOT / "docker" / "studio.Dockerfile").read_text(encoding="utf-8")
    assert re.findall(r'"\.\[([a-z,]+)\]"', studio) == ["azure,portal,extract"]


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
    (root / "domains" / "wind-om").mkdir(parents=True)
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
        orchestration_settings.resolve_pack_path("wind-om")
        == (root / "domains" / "wind-om").resolve()
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
        "DOCWIKI_STUDIO_IDENTITY_CLIENT_ID",
        "DOCWIKI_STUDIO_APP_NAME",
        "DOCWIKI_ENABLE_STUDIO",
        "DOCWIKI_STUDIO_URL",
        "DOCWIKI_MCP_CONNECTION",
        "APPLICATIONINSIGHTS_CONNECTION_STRING",
    ):
        assert name in outputs, name
    assert len(outputs) <= 64, "ARM caps a template at 64 outputs"


def test_compiled_studio_is_fail_closed(compiled: dict[str, Any]) -> None:
    expression = compiled["variables"]["studioPublic"]
    for name in ("enableStudio", "studioClientId", "studioAllowedPrincipals"):
        assert f"parameters('{name}')" in expression, name
    assert "or(" not in expression, "every condition must hold"
    assert compiled["parameters"]["enableStudio"]["defaultValue"] is False
    assert compiled["parameters"]["studioMinReplicas"]["maxValue"] == 1
    resources = compiled["resources"]  # a list, or a dict by symbolic name in newer Bicep
    modules = {
        resource["name"]: resource
        for resource in (resources.values() if isinstance(resources, dict) else resources)
        if resource["type"] == "Microsoft.Resources/deployments"
    }
    assert modules["studioAuth"]["condition"] == "[variables('studioPublic')]"
    app = modules["studioApp"]["properties"]["parameters"]
    assert app["maxReplicas"] == {"value": 1}
    assert app["dormant"] == {"value": "[not(parameters('enableStudio'))]"}
    assert "variables('studioPublic')" in json.dumps(app["ingressMode"])

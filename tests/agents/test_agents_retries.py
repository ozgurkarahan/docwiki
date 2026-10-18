from docwiki.agents_client.client import AgentClientSettings

ENDPOINT = "https://account.services.ai.azure.com/api/projects/project"


def test_agent_calls_retry_twice_by_default() -> None:
    settings = AgentClientSettings.from_env({"DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": ENDPOINT})
    assert settings.max_retries == 2


def test_agent_retries_are_configurable() -> None:
    env = {"DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": ENDPOINT, "DOCWIKI_AGENT_MAX_RETRIES": "0"}
    assert AgentClientSettings.from_env(env).max_retries == 0

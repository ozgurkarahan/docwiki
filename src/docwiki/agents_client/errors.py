"""Errors raised by ``docwiki.agents_client`` (definitions, deployment and invocation)."""

from __future__ import annotations

__all__ = [
    "AgentAuthError",
    "AgentConfigurationError",
    "AgentDefinitionError",
    "AgentInvocationError",
    "AgentNotFoundError",
    "AgentsClientError",
    "DeployError",
]


class AgentsClientError(Exception):
    """Base class of every error raised by this package."""


class AgentDefinitionError(AgentsClientError, ValueError):
    """An ``agent.yaml`` / ``routine.yaml`` file or an instructions file is invalid."""


class AgentConfigurationError(AgentsClientError):
    """A required setting (environment variable, project connection) is missing or wrong."""


class DeployError(AgentsClientError):
    """Creating an agent version or a routine failed."""


class AgentInvocationError(AgentsClientError):
    """Calling a deployed agent through the Responses API failed."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.request_id = request_id


class AgentAuthError(AgentInvocationError):
    """The caller could not authenticate or lacks a role on the Foundry project."""


class AgentNotFoundError(AgentInvocationError):
    """The agent (or the pinned version) does not exist in the Foundry project."""

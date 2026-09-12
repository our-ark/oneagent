"""Reusable conformance suites for OneAgent extension implementations."""

from oneagent.runtime_dependencies import activate_runtime_dependencies


activate_runtime_dependencies()

from our_ark_provider_kit.conformance import (
    CONFORMANCE_API_VERSION,
    AgentRuntimeConformanceMixin,
    ProviderContractConformanceMixin,
    RepositoryProviderConformanceMixin,
    ReviewProviderConformanceMixin,
)

from oneagent.conformance.profile import ProfileCommandCase, ProfileConformanceMixin
from oneagent.conformance.application import ApplicationCompositionConformanceMixin
from oneagent.conformance.extension import (
    AgentExtensionConformanceMixin,
    ExtensionCommandCase,
)
from oneagent.conformance.notification import DurableNotificationConformanceMixin
from oneagent.conformance.schedule import ExtensionScheduleConformanceMixin
from oneagent.conformance.workflow import WorkflowEngineConformanceMixin


__all__ = [
    "CONFORMANCE_API_VERSION",
    "AgentRuntimeConformanceMixin",
    "ApplicationCompositionConformanceMixin",
    "AgentExtensionConformanceMixin",
    "DurableNotificationConformanceMixin",
    "ExtensionCommandCase",
    "ExtensionScheduleConformanceMixin",
    "ProfileCommandCase",
    "ProfileConformanceMixin",
    "ProviderContractConformanceMixin",
    "RepositoryProviderConformanceMixin",
    "ReviewProviderConformanceMixin",
    "WorkflowEngineConformanceMixin",
]

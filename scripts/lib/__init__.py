#!/usr/bin/env python3
"""
Common utilities package for Claude scripts.

Shared models, utilities, and formatters used across
all skills, agents, and utility scripts.
"""

from .base_cli import BaseCLIScript
from .formatters import format_json, format_yaml
from .integrations import (
    IntegrationConfig,
    get_docs_provider,
    get_issue_format,
    get_issues_provider,
    get_vcs_provider,
    list_profiles,
    load_integrations,
    switch_profile,
)
from .models import (
    AgentInfo,
    CIFailure,
    ComponentType,
    GitCommitInfo,
    Issue,
    KanbanEntry,
    LogLevel,
    NameSuggestion,
    OutputFormat,
    ScriptInfo,
    SkillInfo,
    SyntaxCheckResult,
    TestCoverageResult,
    ValidationResult,
)
from .utils import run_command, write_file_safe

__all__ = [
    # Base classes
    "BaseCLIScript",
    # Integrations
    "IntegrationConfig",
    "get_docs_provider",
    "get_issues_provider",
    "get_issue_format",
    "get_vcs_provider",
    "list_profiles",
    "load_integrations",
    "switch_profile",
    # Models
    "AgentInfo",
    "CIFailure",
    "ComponentType",
    "GitCommitInfo",
    "Issue",
    "KanbanEntry",
    "LogLevel",
    "NameSuggestion",
    "OutputFormat",
    "ScriptInfo",
    "SkillInfo",
    "SyntaxCheckResult",
    "TestCoverageResult",
    "ValidationResult",
    # Utils
    "run_command",
    "write_file_safe",
    # Formatters
    "format_json",
    "format_yaml",
]

#!/usr/bin/env python3
"""
Common utilities package for Claude scripts.

Shared models, utilities, validators, and formatters used across
all skills, agents, and utility scripts.
"""

from .base_cli import BaseCLIScript, main_template
from .formatters import (
    format_error,
    format_json,
    format_summary,
    format_table,
    format_text,
    format_validation_result,
    format_yaml,
)
from .integrations import (
    IntegrationConfig,
    get_docs_provider,
    get_issues_provider,
    get_issue_format,
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
from .utils import (
    detect_language,
    extract_params_from_path,
    extract_issue_from_branch,
    format_percentage,
    normalize_name,
    parse_git_remote_url,
    read_file_safe,
    run_command,
    truncate_text,
    write_file_safe,
)
from .validators import (
    validate_component_name,
    validate_script_syntax,
    validate_skill_structure,
    validate_yaml_frontmatter,
)

__all__ = [
    # Base classes
    "BaseCLIScript",
    "main_template",
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
    "detect_language",
    "extract_params_from_path",
    "extract_issue_from_branch",
    "format_percentage",
    "normalize_name",
    "parse_git_remote_url",
    "read_file_safe",
    "run_command",
    "truncate_text",
    "write_file_safe",
    # Validators
    "validate_component_name",
    "validate_script_syntax",
    "validate_skill_structure",
    "validate_yaml_frontmatter",
    # Formatters
    "format_error",
    "format_json",
    "format_summary",
    "format_table",
    "format_text",
    "format_validation_result",
    "format_yaml",
]

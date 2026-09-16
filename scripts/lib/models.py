#!/usr/bin/env python3
"""
Shared data models for all scripts.

Used across skills, agents, and utility scripts for consistency.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ComponentType(Enum):
    """Type of component (skill, script, agent)."""
    SKILL = "skill"
    SCRIPT = "script"
    AGENT = "agent"


class OutputFormat(Enum):
    """Output format options."""
    JSON = "json"
    YAML = "yaml"
    TEXT = "text"


class LogLevel(Enum):
    """Logging levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class NameSuggestion:
    """Name suggestion with reasoning."""
    name: str
    reasoning: str
    pattern: str  # e.g., "verb-noun", "noun-verb"
    confidence: float = 1.0  # 0.0-1.0


@dataclass
class SkillInfo:
    """Skill metadata from YAML frontmatter."""
    name: str
    description: str
    tools: list[str] = field(default_factory=list)
    model: str = "sonnet"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInfo:
    """Agent metadata from YAML frontmatter."""
    name: str
    description: str
    tools: list[str] = field(default_factory=list)
    model: str = "sonnet"
    color: str = "blue"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScriptInfo:
    """Script metadata."""
    name: str
    path: Path
    language: str  # "python", "powershell", "bash"
    has_tests: bool = False
    test_count: int = 0


@dataclass
class TestCoverageResult:
    """Test coverage analysis result."""
    total_scripts: int
    tested_scripts: int
    untested_scripts: int
    coverage_percent: float
    empty_test_files: int = 0
    total_tests: int = 0
    untested_list: list[str] = field(default_factory=list)
    test_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Generic validation result."""
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SyntaxCheckResult:
    """Syntax validation result."""
    file_path: Path
    language: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    line_number: int | None = None


@dataclass
class GitCommitInfo:
    """Git commit metadata."""
    hash: str
    author: str
    date: str
    message: str
    files_changed: list[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


@dataclass
class Issue:
    """Issue information (format depends on active integration profile)."""
    key: str  # e.g., "#123"
    summary: str
    description: str
    status: str
    assignee: str | None = None
    priority: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class KanbanEntry:
    """KANBAN.md entry."""
    issue_id: str  # e.g., "#123"
    title: str
    status: str  # "TODO", "IN_PROGRESS", "DONE"
    description: str = ""
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CIFailure:
    """CI/CD failure information."""
    job_name: str
    error_message: str
    error_type: str  # "test", "build", "lint", "security"
    file_path: Path | None = None
    line_number: int | None = None
    suggestions: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FileChange:
    """File change with statistics."""
    path: str
    additions: int
    deletions: int
    status: str = "M"  # M=modified, A=added, D=deleted


@dataclass
class BranchCommit:
    """Commit information for branch summary."""
    hash: str
    short_hash: str
    message: str
    author: str
    date: str
    additions: int
    deletions: int
    files_changed: int
    files: list[FileChange] = field(default_factory=list)


@dataclass
class UncommittedChanges:
    """Uncommitted changes in working directory."""
    staged: list[FileChange] = field(default_factory=list)
    unstaged: list[FileChange] = field(default_factory=list)
    untracked: list[FileChange] = field(default_factory=list)


@dataclass
class BranchSummary:
    """Comprehensive branch summary."""
    current_branch: str
    base_branch: str
    commits_count: int
    commits: list[BranchCommit]
    total_additions: int
    total_deletions: int
    unique_files_changed: int
    uncommitted: UncommittedChanges
    has_uncommitted_changes: bool

#!/usr/bin/env python3
"""
Shared utilities for all scripts.

Common functions used across skills, agents, and utility scripts.
"""

import re
import subprocess
from pathlib import Path
from typing import Any

from .models import ComponentType


def read_file_safe(file_path: Path, encoding: str = "utf-8") -> str | None:
    """
    Safely read file with error handling.

    Args:
        file_path: Path to file
        encoding: File encoding (default: utf-8)

    Returns:
        File content or None if error
    """
    try:
        if not file_path.exists():
            return None
        return file_path.read_text(encoding=encoding)
    except Exception:
        return None


def write_file_safe(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """
    Safely write file with error handling.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding (default: utf-8)

    Returns:
        True if success, False otherwise
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding=encoding)
        return True
    except Exception:
        return False


def extract_params_from_path(path: str) -> list[dict[str, str]]:
    """
    Extract parameters from URL/path patterns.

    Supports:
    - Express/Gin style: /users/:id
    - ASP.NET style: /users/{id}

    Args:
        path: URL/path pattern

    Returns:
        List of parameter dicts with name, type, required

    Example:
        >>> extract_params_from_path("/users/:id/posts/{postId}")
        [
            {"name": "id", "param_type": "path", "required": True},
            {"name": "postId", "param_type": "path", "required": True}
        ]
    """
    params = []
    seen = set()

    # Pattern 1: Express/Gin style (:param)
    colon_params = re.findall(r":(\w+)", path)
    for param in colon_params:
        if param not in seen:
            params.append({
                "name": param,
                "param_type": "path",
                "data_type": "string",
                "required": True
            })
            seen.add(param)

    # Pattern 2: ASP.NET/Spring style ({param})
    brace_params = re.findall(r"\{(\w+)\}", path)
    for param in brace_params:
        if param not in seen:
            params.append({
                "name": param,
                "param_type": "path",
                "data_type": "string",
                "required": True
            })
            seen.add(param)

    return params


def normalize_name(name: str, component_type: ComponentType) -> str:
    """
    Normalize component name to lowercase-with-dashes.

    Args:
        name: Original name
        component_type: Type of component (skill, script, agent)

    Returns:
        Normalized name (lowercase-with-dashes)

    Example:
        >>> normalize_name("Analyze Code", ComponentType.SKILL)
        "analyze-code"
    """
    # Remove special characters
    name = re.sub(r"[^\w\s-]", "", name)

    # Replace spaces/underscores with dashes
    name = re.sub(r"[\s_]+", "-", name)

    # Convert to lowercase
    name = name.lower()

    # Remove leading/trailing dashes
    name = name.strip("-")

    # Remove extension if present (for scripts)
    if component_type == ComponentType.SCRIPT:
        name = re.sub(r"\.(py|ps1|sh)$", "", name)

    return name


def detect_language(file_path: Path) -> str | None:
    """
    Detect programming language from file extension.

    Args:
        file_path: Path to file

    Returns:
        Language name or None if unknown
    """
    extension_map = {
        ".py": "python",
        ".ps1": "powershell",
        ".psm1": "powershell",
        ".sh": "bash",
        ".bash": "bash",
        ".js": "javascript",
        ".ts": "typescript",
        ".go": "go",
        ".cs": "csharp",
        ".java": "java",
        ".rb": "ruby",
        ".pl": "perl",
    }

    suffix = file_path.suffix.lower()
    return extension_map.get(suffix)


def run_command(
    command: list[str],
    cwd: Path | None = None,
    timeout: int = 30
) -> tuple[int, str, str]:
    """
    Run shell command and return result.

    Args:
        command: Command and arguments as list
        cwd: Working directory (optional)
        timeout: Timeout in seconds

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length with suffix.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format percentage value.

    Args:
        value: Percentage (0.0-100.0)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string

    Example:
        >>> format_percentage(67.8945)
        "67.89%"
    """
    return f"{value:.{decimals}f}%"


def parse_git_remote_url(url: str) -> dict[str, str] | None:
    """
    Parse git remote URL to extract owner/repo.

    Supports:
    - HTTPS: https://github.com/owner/repo.git
    - SSH: git@github.com:owner/repo.git

    Args:
        url: Git remote URL

    Returns:
        Dict with owner, repo, host or None if invalid

    Example:
        >>> parse_git_remote_url("https://github.com/anthropics/claude-code.git")
        {"owner": "anthropics", "repo": "claude-code", "host": "github.com"}
    """
    # HTTPS pattern
    https_match = re.match(r"https?://([^/]+)/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if https_match:
        return {
            "host": https_match.group(1),
            "owner": https_match.group(2),
            "repo": https_match.group(3),
        }

    # SSH pattern
    ssh_match = re.match(r"git@([^:]+):([^/]+)/([^/]+?)(?:\.git)?$", url)
    if ssh_match:
        return {
            "host": ssh_match.group(1),
            "owner": ssh_match.group(2),
            "repo": ssh_match.group(3),
        }

    return None


def extract_issue_from_branch(branch_name: str) -> str | None:
    r"""
    Extract issue ID from branch name using active integration profile.

    Uses issue_format from active profile (e.g., r"#(\d+)" for GitHub).

    Args:
        branch_name: Git branch name

    Returns:
        Issue ID or None if not found

    Example:
        >>> extract_issue_from_branch("feature/#123-add-auth")
        "#123"
    """
    from common.integrations import get_issue_format

    issue_pattern = get_issue_format()
    match = re.search(issue_pattern, branch_name)
    if match:
        return match.group(0)

    return None

#!/usr/bin/env python3
"""
Integration configuration loader.

Loads profile-based integration settings from separate JSON files.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class IntegrationConfig:
    """Integration configuration for a profile."""
    profile_name: str
    vcs_provider: str
    vcs_url: str
    vcs_api_url: str
    ci_provider: str
    docs_provider: str
    docs_url: Optional[str]
    issues_provider: str
    issues_url: Optional[str]
    issue_format: str


def _get_integrations_dir() -> Path:
    """Get integrations directory."""
    return Path.home() / ".claude" / "integrations"


def _get_active_profile() -> str:
    """
    Get active profile name with auto-detection by path.

    Priority:
    1. Path-based auto-detection (path-mappings.local.json)
    2. Global .active file
    3. Default fallback

    Returns:
        Profile name to use.
    """
    integrations_dir = _get_integrations_dir()

    # 1. Check path-mappings.local.json for auto-detection
    mapping_file = integrations_dir / "path-mappings.local.json"
    if mapping_file.exists():
        try:
            cwd = str(Path.cwd()).replace("\\", "/")
            mappings = json.loads(mapping_file.read_text(encoding="utf-8"))

            # Find first matching path (most specific first)
            for mapping in mappings.get("mappings", []):
                path = mapping["path"].replace("\\", "/")
                if cwd.startswith(path):
                    return mapping["profile"]
        except (json.JSONDecodeError, KeyError):
            pass  # Ignore invalid mapping file

    # 2. Check global .active file
    active_file = integrations_dir / ".active"
    if active_file.exists():
        return active_file.read_text(encoding="utf-8").strip()

    # 3. Default fallback
    return "default"


def load_integrations(profile: Optional[str] = None) -> IntegrationConfig:
    """
    Load integration config from ~/.claude/integrations/{profile}.json.

    Args:
        profile: Profile name to load. If None, uses active profile from .active file.

    Returns:
        IntegrationConfig with provider settings.

    Raises:
        FileNotFoundError: If profile file not found.
        ValueError: If profile config invalid.
    """
    integrations_dir = _get_integrations_dir()

    # Determine which profile to use
    profile_name = profile or _get_active_profile()

    profile_file = integrations_dir / f"{profile_name}.json"

    if not profile_file.exists():
        # Fallback to default (GitHub)
        return IntegrationConfig(
            profile_name="default",
            vcs_provider="github",
            vcs_url="https://github.com",
            vcs_api_url="https://api.github.com",
            ci_provider="github-actions",
            docs_provider="github-pages",
            docs_url=None,
            issues_provider="github",
            issues_url=None,
            issue_format=r"#(\d+)"
        )

    with open(profile_file, "r", encoding="utf-8") as f:
        profile_config = json.load(f)

    return IntegrationConfig(
        profile_name=profile_name,
        vcs_provider=profile_config["vcs"]["provider"],
        vcs_url=profile_config["vcs"]["url"],
        vcs_api_url=profile_config["vcs"].get("api_url", ""),
        ci_provider=profile_config["ci"]["provider"],
        docs_provider=profile_config["docs"]["provider"],
        docs_url=profile_config["docs"].get("url"),
        issues_provider=profile_config["issues"]["provider"],
        issues_url=profile_config["issues"].get("url"),
        issue_format=profile_config["issues"]["issue_format"]
    )


def list_profiles() -> list[str]:
    """
    List all available integration profiles.

    Returns:
        List of profile names (without .json extension).
    """
    integrations_dir = _get_integrations_dir()

    if not integrations_dir.exists():
        return ["default"]  # Default

    profiles = []
    for file in integrations_dir.glob("*.json"):
        profiles.append(file.stem)

    return sorted(profiles)


def get_vcs_provider() -> str:
    """Get current VCS provider."""
    config = load_integrations()
    return config.vcs_provider


def get_issues_provider() -> str:
    """Get current issues provider."""
    config = load_integrations()
    return config.issues_provider


def get_docs_provider() -> str:
    """Get current docs provider."""
    config = load_integrations()
    return config.docs_provider


def get_issue_format() -> str:
    """Get regex pattern for issue ID extraction."""
    config = load_integrations()
    return config.issue_format


def validate_profile(profile_path: Path) -> list[str]:
    """
    Validate profile JSON structure and content.

    Args:
        profile_path: Path to profile JSON file.

    Returns:
        List of error messages (empty if valid).
    """
    errors = []

    if not profile_path.exists():
        return [f"Profile file not found: {profile_path}"]

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile_config = json.load(f)
    except json.JSONDecodeError as e:
        return [f"Invalid JSON: {e}"]

    # Check required top-level fields
    required_fields = ["name", "vcs", "ci", "docs", "issues"]
    for field in required_fields:
        if field not in profile_config:
            errors.append(f"Missing required field: {field}")

    # Validate VCS config
    if "vcs" in profile_config:
        vcs = profile_config["vcs"]
        if not isinstance(vcs, dict):
            errors.append("'vcs' must be an object")
        else:
            if "provider" not in vcs:
                errors.append("'vcs.provider' is required")
            if "url" not in vcs:
                errors.append("'vcs.url' is required")

    # Validate CI config
    if "ci" in profile_config:
        ci = profile_config["ci"]
        if not isinstance(ci, dict):
            errors.append("'ci' must be an object")
        else:
            if "provider" not in ci:
                errors.append("'ci.provider' is required")

    # Validate docs config
    if "docs" in profile_config:
        docs = profile_config["docs"]
        if not isinstance(docs, dict):
            errors.append("'docs' must be an object")
        else:
            if "provider" not in docs:
                errors.append("'docs.provider' is required")

    # Validate issues config
    if "issues" in profile_config:
        issues = profile_config["issues"]
        if not isinstance(issues, dict):
            errors.append("'issues' must be an object")
        else:
            if "provider" not in issues:
                errors.append("'issues.provider' is required")
            if "issue_format" not in issues:
                errors.append("'issues.issue_format' is required")
            else:
                # Validate regex
                import re
                try:
                    re.compile(issues["issue_format"])
                except re.error as e:
                    errors.append(f"Invalid regex in 'issues.issue_format': {e}")

    return errors


def get_profile_detection_info() -> dict[str, str]:
    """
    Get information about how the active profile was detected.

    Returns:
        Dict with profile_name, detection_source, and details.
    """
    integrations_dir = _get_integrations_dir()

    # Check path-mappings.local.json
    mapping_file = integrations_dir / "path-mappings.local.json"
    if mapping_file.exists():
        try:
            cwd = str(Path.cwd()).replace("\\", "/")
            mappings = json.loads(mapping_file.read_text(encoding="utf-8"))

            for mapping in mappings.get("mappings", []):
                path = mapping["path"].replace("\\", "/")
                if cwd.startswith(path):
                    return {
                        "profile_name": mapping["profile"],
                        "detection_source": "path-mapping",
                        "details": f"Matched path: {path}",
                        "cwd": cwd
                    }
        except (json.JSONDecodeError, KeyError):
            pass

    # Check .active file
    active_file = integrations_dir / ".active"
    if active_file.exists():
        return {
            "profile_name": active_file.read_text(encoding="utf-8").strip(),
            "detection_source": "global .active file",
            "details": str(active_file),
            "cwd": str(Path.cwd())
        }

    # Default fallback
    return {
        "profile_name": "default",
        "detection_source": "default fallback",
        "details": "No profile configured",
        "cwd": str(Path.cwd())
    }


def get_issue_url(repo: str, issue_id: str) -> str:
    """
    Build issue URL for active profile.

    Args:
        repo: Repository path (e.g., "owner/repo")
        issue_id: Issue ID (e.g., "#123", "PROJ-456")

    Returns:
        Full issue URL.

    Example:
        >>> get_issue_url("owner/repo", "#123")
        "https://github.com/owner/repo/issues/123"
    """
    config = load_integrations()

    # Remove # prefix if present
    issue_id_clean = issue_id.lstrip("#")

    if config.issues_provider == "github":
        return f"{config.vcs_url}/{repo}/issues/{issue_id_clean}"
    elif config.issues_provider == "gitlab":
        return f"{config.vcs_url}/{repo}/-/issues/{issue_id_clean}"
    elif config.issues_provider == "azure-devops":
        # Azure DevOps: org/project/_workitems/edit/123
        return f"{config.vcs_url}/{repo}/_workitems/edit/{issue_id_clean}"
    else:
        # Generic fallback
        return f"{config.issues_url or config.vcs_url}/{repo}/issues/{issue_id_clean}"


def get_pr_url(repo: str, pr_id: str) -> str:
    """
    Build pull/merge request URL for active profile.

    Args:
        repo: Repository path (e.g., "owner/repo")
        pr_id: PR/MR ID (e.g., "123")

    Returns:
        Full PR/MR URL.

    Example:
        >>> get_pr_url("owner/repo", "123")
        "https://github.com/owner/repo/pull/123"
    """
    config = load_integrations()

    # Remove # prefix if present
    pr_id_clean = pr_id.lstrip("#")

    if config.vcs_provider == "github":
        return f"{config.vcs_url}/{repo}/pull/{pr_id_clean}"
    elif config.vcs_provider == "gitlab":
        return f"{config.vcs_url}/{repo}/-/merge_requests/{pr_id_clean}"
    elif config.vcs_provider == "azure-devops":
        return f"{config.vcs_url}/{repo}/_git/pullrequest/{pr_id_clean}"
    else:
        # Generic fallback
        return f"{config.vcs_url}/{repo}/pull/{pr_id_clean}"


def switch_profile(profile_name: str):
    """
    Switch active profile by writing to .active file.

    Args:
        profile_name: Profile to activate.

    Raises:
        FileNotFoundError: If profile file not found.
    """
    integrations_dir = _get_integrations_dir()
    profile_file = integrations_dir / f"{profile_name}.json"

    if not profile_file.exists():
        raise FileNotFoundError(f"Profile '{profile_name}' not found at {profile_file}")

    active_file = integrations_dir / ".active"
    active_file.write_text(profile_name, encoding="utf-8")

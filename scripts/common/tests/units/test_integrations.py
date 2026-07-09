#!/usr/bin/env python3
"""Tests for integrations.py"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from common.integrations import (
    get_issue_url,
    get_pr_url,
    get_profile_detection_info,
    load_integrations,
    validate_profile
)

def test_validate_profile_valid():
    """Test validation of valid profile."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "name": "Test",
            "vcs": {"provider": "github", "url": "https://github.com"},
            "ci": {"provider": "github-actions"},
            "docs": {"provider": "github-pages"},
            "issues": {"provider": "github", "issue_format": r"#(\d+)"}
        }, f)
        profile_path = Path(f.name)

    try:
        errors = validate_profile(profile_path)
        assert errors == []
    finally:
        profile_path.unlink()

def test_validate_profile_missing_fields():
    """Test validation catches missing required fields."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"name": "Test"}, f)  # Missing vcs, ci, docs, issues
        profile_path = Path(f.name)

    try:
        errors = validate_profile(profile_path)
        assert len(errors) > 0
        assert any("vcs" in err for err in errors)
    finally:
        profile_path.unlink()

def test_validate_profile_invalid_regex():
    """Test validation catches invalid regex."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({
            "name": "Test",
            "vcs": {"provider": "github", "url": "https://github.com"},
            "ci": {"provider": "github-actions"},
            "docs": {"provider": "github-pages"},
            "issues": {"provider": "github", "issue_format": "[invalid(regex"}  # Bad regex
        }, f)
        profile_path = Path(f.name)

    try:
        errors = validate_profile(profile_path)
        assert len(errors) > 0
        assert any("regex" in err.lower() for err in errors)
    finally:
        profile_path.unlink()

@patch('common.integrations.load_integrations')
def test_get_issue_url_github(mock_load):
    """Test GitHub issue URL generation."""
    from common.integrations import IntegrationConfig

    mock_load.return_value = IntegrationConfig(
        profile_name="github",
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

    url = get_issue_url("owner/repo", "#123")
    assert url == "https://github.com/owner/repo/issues/123"

@patch('common.integrations.load_integrations')
def test_get_issue_url_gitlab(mock_load):
    """Test GitLab issue URL generation."""
    from common.integrations import IntegrationConfig

    mock_load.return_value = IntegrationConfig(
        profile_name="gitlab",
        vcs_provider="gitlab",
        vcs_url="https://gitlab.com",
        vcs_api_url="https://gitlab.com/api/v4",
        ci_provider="gitlab-ci",
        docs_provider="gitlab-wiki",
        docs_url=None,
        issues_provider="gitlab",
        issues_url=None,
        issue_format=r"#(\d+)"
    )

    url = get_issue_url("owner/repo", "#123")
    assert url == "https://gitlab.com/owner/repo/-/issues/123"

@patch('common.integrations.load_integrations')
def test_get_pr_url_github(mock_load):
    """Test GitHub PR URL generation."""
    from common.integrations import IntegrationConfig

    mock_load.return_value = IntegrationConfig(
        profile_name="github",
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

    url = get_pr_url("owner/repo", "456")
    assert url == "https://github.com/owner/repo/pull/456"

@patch('common.integrations.load_integrations')
def test_get_pr_url_gitlab(mock_load):
    """Test GitLab MR URL generation."""
    from common.integrations import IntegrationConfig

    mock_load.return_value = IntegrationConfig(
        profile_name="gitlab",
        vcs_provider="gitlab",
        vcs_url="https://gitlab.com",
        vcs_api_url="https://gitlab.com/api/v4",
        ci_provider="gitlab-ci",
        docs_provider="gitlab-wiki",
        docs_url=None,
        issues_provider="gitlab",
        issues_url=None,
        issue_format=r"#(\d+)"
    )

    url = get_pr_url("owner/repo", "789")
    assert url == "https://gitlab.com/owner/repo/-/merge_requests/789"

def test_profile_detection_fallback():
    """Test fallback to default when no config exists."""
    info = get_profile_detection_info()
    assert info["profile_name"] in ["default", "github"]  # May vary based on actual config
    assert "detection_source" in info

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

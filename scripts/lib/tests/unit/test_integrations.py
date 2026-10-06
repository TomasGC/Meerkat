#!/usr/bin/env python3
"""Tests for integrations.py"""

import json
import tempfile
from pathlib import Path

import pytest

from lib import integrations
from lib.integrations import get_profile_detection_info, validate_profile


def test_validate_profile_valid():
    """Test validation of valid profile."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(
            {
                "name": "Test",
                "vcs": {"provider": "github", "url": "https://github.com"},
                "ci": {"provider": "github-actions"},
                "docs": {"provider": "github-pages"},
                "issues": {"provider": "github", "issue_format": r"#(\d+)"},
            },
            f,
        )
        profile_path = Path(f.name)

    try:
        errors = validate_profile(profile_path)
        assert errors == []
    finally:
        profile_path.unlink()


def test_validate_profile_missing_fields():
    """Test validation catches missing required fields."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(
            {
                "name": "Test",
                "vcs": {"provider": "github", "url": "https://github.com"},
                "ci": {"provider": "github-actions"},
                "docs": {"provider": "github-pages"},
                "issues": {"provider": "github", "issue_format": "[invalid(regex"},  # Bad regex
            },
            f,
        )
        profile_path = Path(f.name)

    try:
        errors = validate_profile(profile_path)
        assert len(errors) > 0
        assert any("regex" in err.lower() for err in errors)
    finally:
        profile_path.unlink()


def test_profile_detection_fallback():
    """Test fallback to default when no config exists."""
    info = get_profile_detection_info()
    assert info["profile_name"] in ["default", "github"]  # May vary based on actual config
    assert "detection_source" in info


# ── profiles under an isolated MEERKAT_HOME ──────────────────────────────────

_GITLAB = {
    "name": "GitLab",
    "vcs": {"provider": "gitlab", "url": "https://gitlab.example.com"},
    "ci": {"provider": "gitlab-ci"},
    "docs": {"provider": "gitlab-wiki", "url": "https://docs.example.com"},
    "issues": {"provider": "jira", "url": "https://jira.example.com", "issue_format": r"[A-Z]+-\d+"},
}


@pytest.fixture
def integrations_dir(tmp_path, monkeypatch):
    """An empty integrations/ directory the module resolves through MEERKAT_HOME."""
    monkeypatch.setenv("MEERKAT_HOME", str(tmp_path))
    directory = tmp_path / "integrations"
    directory.mkdir()
    return directory


def test_load_integrations_without_profile_file_falls_back_to_github(integrations_dir):
    config = integrations.load_integrations("missing")
    assert config.profile_name == "default"
    assert config.vcs_provider == "github"
    assert config.issue_format == r"#(\d+)"


def test_load_integrations_reads_named_profile(integrations_dir):
    (integrations_dir / "gitlab.json").write_text(json.dumps(_GITLAB), encoding="utf-8")

    config = integrations.load_integrations("gitlab")

    assert config.profile_name == "gitlab"
    assert config.vcs_url == "https://gitlab.example.com"
    assert config.vcs_api_url == ""  # optional field absent
    assert config.docs_url == "https://docs.example.com"
    assert config.issues_url == "https://jira.example.com"
    assert config.issue_format == r"[A-Z]+-\d+"


def test_active_file_selects_profile_for_provider_getters(integrations_dir):
    (integrations_dir / "gitlab.json").write_text(json.dumps(_GITLAB), encoding="utf-8")
    (integrations_dir / ".active").write_text("gitlab\n", encoding="utf-8")

    assert integrations.get_vcs_provider() == "gitlab"
    assert integrations.get_issues_provider() == "jira"
    assert integrations.get_docs_provider() == "gitlab-wiki"
    assert integrations.get_issue_format() == r"[A-Z]+-\d+"


def test_path_mapping_wins_over_active_file(integrations_dir, tmp_path, monkeypatch):
    work = tmp_path / "work" / "repo"
    work.mkdir(parents=True)
    monkeypatch.chdir(work)
    mapping = {"mappings": [{"path": str(tmp_path / "work"), "profile": "gitlab"}]}
    (integrations_dir / "path-mappings.local.json").write_text(json.dumps(mapping), encoding="utf-8")
    (integrations_dir / ".active").write_text("other", encoding="utf-8")

    assert integrations._get_active_profile() == "gitlab"
    info = get_profile_detection_info()
    assert info["profile_name"] == "gitlab"
    assert info["detection_source"] == "path-mapping"


def test_invalid_path_mapping_falls_through_to_active_file(integrations_dir):
    (integrations_dir / "path-mappings.local.json").write_text("{not json", encoding="utf-8")
    (integrations_dir / ".active").write_text("gitlab", encoding="utf-8")

    assert integrations._get_active_profile() == "gitlab"
    info = get_profile_detection_info()
    assert info["profile_name"] == "gitlab"
    assert info["detection_source"] == "global .active file"


def test_no_profile_configured_reports_default(integrations_dir):
    assert integrations._get_active_profile() == "default"
    assert get_profile_detection_info()["detection_source"] == "default fallback"


def test_list_profiles_sorted(integrations_dir):
    for name in ("zeta", "alpha"):
        (integrations_dir / f"{name}.json").write_text("{}", encoding="utf-8")
    assert integrations.list_profiles() == ["alpha", "zeta"]


def test_list_profiles_without_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("MEERKAT_HOME", str(tmp_path))
    assert integrations.list_profiles() == ["default"]


def test_switch_profile_writes_active_file(integrations_dir):
    (integrations_dir / "gitlab.json").write_text("{}", encoding="utf-8")
    integrations.switch_profile("gitlab")
    assert (integrations_dir / ".active").read_text(encoding="utf-8") == "gitlab"


def test_switch_profile_unknown_raises(integrations_dir):
    with pytest.raises(FileNotFoundError, match="nope"):
        integrations.switch_profile("nope")


def test_validate_profile_missing_file(tmp_path):
    assert validate_profile(tmp_path / "x.json") == [f"Profile file not found: {tmp_path / 'x.json'}"]


def test_validate_profile_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{", encoding="utf-8")
    assert validate_profile(path)[0].startswith("Invalid JSON")


def test_validate_profile_sections_must_be_objects(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"name": "x", "vcs": [], "ci": 1, "docs": "d", "issues": None}), encoding="utf-8")
    assert validate_profile(path) == [
        "'vcs' must be an object",
        "'ci' must be an object",
        "'docs' must be an object",
        "'issues' must be an object",
    ]


def test_validate_profile_reports_missing_nested_fields(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"name": "x", "vcs": {}, "ci": {}, "docs": {}, "issues": {}}), encoding="utf-8")
    assert validate_profile(path) == [
        "'vcs.provider' is required",
        "'vcs.url' is required",
        "'ci.provider' is required",
        "'docs.provider' is required",
        "'issues.provider' is required",
        "'issues.issue_format' is required",
    ]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

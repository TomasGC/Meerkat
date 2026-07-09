"""Tests for switch-profile.py — integration profile switcher."""

import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load switch-profile.py via importlib (hyphen in filename prevents normal import)
_SCRIPT_PATH = Path(__file__).parent.parent.parent / "cli" / "switch-profile.py"
_spec = importlib.util.spec_from_file_location("switch_profile_cli", _SCRIPT_PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore
_spec.loader.exec_module(_mod)  # type: ignore
SwitchProfileScript = _mod.SwitchProfileScript

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_config(profile_name: str = "default") -> MagicMock:
    config = MagicMock()
    config.profile_name = profile_name
    config.vcs_provider = "github"
    config.ci_provider = "github-actions"
    config.docs_provider = "github-pages"
    config.issues_provider = "github"
    config.vcs_url = "https://github.com"
    config.issue_format = r"#(\d+)"
    return config

def _args(**kwargs):
    import argparse
    defaults = dict(list=False, status=False, create=None, validate=None, profile=None)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def script():
    return SwitchProfileScript()

@pytest.fixture
def integrations_dir(tmp_path: Path) -> Path:
    d = tmp_path / ".claude" / "integrations"
    d.mkdir(parents=True)
    (d / "default.json").write_text(json.dumps({
        "name": "Default",
        "vcs": {"provider": "github", "url": "https://github.com", "api_url": "https://api.github.com"},
        "ci": {"provider": "github-actions"},
        "docs": {"provider": "github-pages"},
        "issues": {"provider": "github", "issue_format": r"#(\d+)"}
    }))
    return d

# ---------------------------------------------------------------------------
# Unit: missing integrations dir
# ---------------------------------------------------------------------------

def test_missing_integrations_dir(script, tmp_path):
    with patch.object(_mod.Path, "home", return_value=tmp_path / "nohome"):
        result = script.execute(_args())
    assert result["success"] is False
    assert "not found" in result["error"]

# ---------------------------------------------------------------------------
# Unit: show current profile
# ---------------------------------------------------------------------------

def test_show_current_profile(script, integrations_dir):
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        with patch.object(_mod, "load_integrations", return_value=_make_mock_config()):
            result = script.execute(_args())
    assert result["success"] is True
    assert result["active_profile"] == "default"
    assert result["vcs_provider"] == "github"

# ---------------------------------------------------------------------------
# Unit: list profiles
# ---------------------------------------------------------------------------

def test_list_profiles(script, integrations_dir):
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        with patch.object(_mod, "list_profiles", return_value=["default", "work"]):
            with patch.object(_mod, "load_integrations", return_value=_make_mock_config()):
                result = script.execute(_args(list=True))
    assert result["success"] is True
    assert len(result["profiles"]) == 2
    assert result["active_profile"] == "default"

# ---------------------------------------------------------------------------
# Unit: switch profile
# ---------------------------------------------------------------------------

def test_switch_profile_success(script, integrations_dir):
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        with patch.object(_mod, "switch_profile") as mock_switch:
            result = script.execute(_args(profile="work"))
    mock_switch.assert_called_once_with("work")
    assert result["success"] is True
    assert result["active_profile"] == "work"

def test_switch_profile_not_found(script, integrations_dir):
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        with patch.object(_mod, "switch_profile", side_effect=FileNotFoundError("not found")):
            result = script.execute(_args(profile="ghost"))
    assert result["success"] is False
    assert "error" in result

def test_switch_profile_invalid(script, integrations_dir):
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        with patch.object(_mod, "switch_profile", side_effect=ValueError("invalid")):
            result = script.execute(_args(profile="??"))
    assert result["success"] is False

# ---------------------------------------------------------------------------
# Unit: validate profile
# ---------------------------------------------------------------------------

def test_validate_profile_valid(script, integrations_dir):
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        with patch.object(_mod, "validate_profile", return_value=[]):
            result = script.execute(_args(validate="default"))
    assert result["success"] is True
    assert result["profile"] == "default"

def test_validate_profile_invalid(script, integrations_dir):
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        with patch.object(_mod, "validate_profile", return_value=["Missing vcs.provider"]):
            result = script.execute(_args(validate="broken"))
    assert result["success"] is False
    assert len(result["errors"]) > 0

# ---------------------------------------------------------------------------
# Unit: create profile
# ---------------------------------------------------------------------------

def test_create_profile_new(script, integrations_dir):
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        result = script.execute(_args(create="newprofile"))
    assert result["success"] is True
    assert result["profile"] == "newprofile"
    assert (integrations_dir / "newprofile.json").exists()

def test_create_profile_already_exists(script, integrations_dir):
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        result = script.execute(_args(create="default"))
    assert result["success"] is False
    assert "already exists" in result["error"]

# ---------------------------------------------------------------------------
# Unit: status
# ---------------------------------------------------------------------------

def test_show_status(script, integrations_dir):
    detection_info = {
        "detection_source": "file", "details": "found .active", "cwd": str(integrations_dir)
    }
    with patch.object(_mod.Path, "home", return_value=integrations_dir.parent.parent):
        with patch.object(_mod, "get_profile_detection_info", return_value=detection_info):
            with patch.object(_mod, "load_integrations", return_value=_make_mock_config()):
                result = script.execute(_args(status=True))
    assert result["success"] is True
    assert result["detection_source"] == "file"
    assert result["vcs_provider"] == "github"

#!/usr/bin/env python3
"""Tests for resume_project_common.py"""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports

from cli.resume_project_common import (
    validate_project_setup,
    check_claude_cli,
    convert_to_git_bash_path,
    resume_project
)

class TestValidateProjectSetup:
    """Test project setup validation."""

    def test_with_kanban(self, tmp_path, capsys):
        """Test validation when KANBAN.md exists."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        kanban_file = claude_dir / "KANBAN.md"
        kanban_file.write_text("# KANBAN\n")

        result = validate_project_setup(tmp_path)

        assert result is True
        captured = capsys.readouterr()
        assert "Instructions auto-loaded from CLAUDE.md" in captured.out
        assert "[OK] Task tracking found: KANBAN.md" in captured.out

    def test_without_kanban(self, tmp_path, capsys):
        """Test validation when KANBAN.md doesn't exist."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        result = validate_project_setup(tmp_path)

        assert result is True
        captured = capsys.readouterr()
        assert "[WARN] No task tracking yet" in captured.out

    def test_no_claude_directory(self, tmp_path, capsys):
        """Test validation when .claude/ doesn't exist."""
        result = validate_project_setup(tmp_path)

        assert result is True
        captured = capsys.readouterr()
        assert "[WARN] No task tracking yet" in captured.out

class TestCheckClaudeCli:
    """Test Claude CLI availability check."""

    @patch("cli.resume_project_common.shutil.which")
    def test_claude_cli_available(self, mock_which):
        """Test when Claude CLI is available."""
        mock_which.return_value = "/usr/local/bin/claude"

        result = check_claude_cli()

        assert result is True
        mock_which.assert_called_once_with("claude")

    @patch("cli.resume_project_common.shutil.which")
    def test_claude_cli_not_available(self, mock_which, capsys):
        """Test when Claude CLI is not available."""
        mock_which.return_value = None

        result = check_claude_cli()

        assert result is False
        captured = capsys.readouterr()
        assert "Claude Code CLI not found" in captured.err

class TestConvertToGitBashPath:
    """Test Windows path to Git Bash path conversion."""

    def test_windows_path_c_drive(self):
        """Test conversion of C: drive path."""
        path = Path("C:/Users/tomas/project")
        result = convert_to_git_bash_path(path)

        assert result == "/c/Users/tomas/project"

    def test_windows_path_d_drive(self):
        """Test conversion of D: drive path."""
        path = Path("D:/workspace/myproject")
        result = convert_to_git_bash_path(path)

        assert result == "/d/workspace/myproject"

    def test_windows_path_with_backslashes(self):
        """Test conversion with backslashes."""
        path = Path("C:\\Users\\tomas\\project")
        result = convert_to_git_bash_path(path)

        # Path should be normalized
        assert "/c/" in result or "C:/" in result

    def test_unix_path(self):
        """Test Unix path (no conversion needed)."""
        path = Path("/home/tomas/project")
        result = convert_to_git_bash_path(path)

        assert result == "/home/tomas/project"

class TestResumeProject:
    """Test main resume_project function."""

    @patch("cli.resume_project_common.subprocess.run")
    @patch("cli.resume_project_common.check_claude_cli")
    def test_successful_resume(self, mock_check, mock_run, tmp_path, capsys):
        """Test successful project resume."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        # Create .claude directory
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        result = resume_project("TestProject", "Test description", tmp_path)

        assert result == 0
        mock_check.assert_called_once()
        mock_run.assert_called_once()

        captured = capsys.readouterr()
        assert "TestProject" in captured.out
        assert "Resume Claude" in captured.out
        assert "Launching Claude Code" in captured.out

    def test_missing_project_name(self, tmp_path, capsys):
        """Test error when project_name is missing."""
        result = resume_project("", "Description", tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "project_name must be provided" in captured.err

    def test_missing_project_description(self, tmp_path, capsys):
        """Test error when project_description is missing."""
        result = resume_project("Name", "", tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "project_description must be provided" in captured.err

    def test_missing_project_root(self, capsys):
        """Test error when project_root is missing."""
        result = resume_project("Name", "Description", None)

        assert result == 1
        captured = capsys.readouterr()
        assert "project_root must be provided" in captured.err

    def test_project_root_not_exists(self, capsys):
        """Test error when project root doesn't exist."""
        result = resume_project(
            "Name",
            "Description",
            Path("/nonexistent/path")
        )

        assert result == 1
        captured = capsys.readouterr()
        assert "Project root not found" in captured.err

    @patch("cli.resume_project_common.check_claude_cli")
    def test_claude_cli_not_found(self, mock_check, tmp_path):
        """Test error when Claude CLI is not available."""
        mock_check.return_value = False

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        result = resume_project("Name", "Description", tmp_path)

        assert result == 1

    @patch("cli.resume_project_common.subprocess.run")
    @patch("cli.resume_project_common.check_claude_cli")
    def test_subprocess_error(self, mock_check, mock_run, tmp_path, capsys):
        """Test error when subprocess fails."""
        mock_check.return_value = True
        mock_run.side_effect = subprocess.CalledProcessError(1, "claude")

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        result = resume_project("Name", "Description", tmp_path)

        assert result == 1
        captured = capsys.readouterr()
        assert "Failed to launch Claude" in captured.err

    @patch("cli.resume_project_common.subprocess.run")
    @patch("cli.resume_project_common.check_claude_cli")
    def test_keyboard_interrupt(self, mock_check, mock_run, tmp_path, capsys):
        """Test graceful handling of keyboard interrupt."""
        mock_check.return_value = True
        mock_run.side_effect = KeyboardInterrupt()

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        result = resume_project("Name", "Description", tmp_path)

        assert result == 0
        captured = capsys.readouterr()
        assert "interrupted by user" in captured.out

    @patch("cli.resume_project_common.subprocess.run")
    @patch("cli.resume_project_common.check_claude_cli")
    def test_banner_display(self, mock_check, mock_run, tmp_path, capsys):
        """Test that banner is displayed correctly."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        resume_project("MyProject", "Python 3.12 app", tmp_path)

        captured = capsys.readouterr()
        assert "MyProject - Resume Claude" in captured.out
        assert "=" in captured.out

    @patch("cli.resume_project_common.subprocess.run")
    @patch("cli.resume_project_common.check_claude_cli")
    def test_kanban_status_display(self, mock_check, mock_run, tmp_path, capsys):
        """Test KANBAN status display."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        kanban = claude_dir / "KANBAN.md"
        kanban.write_text("# KANBAN\n")

        resume_project("Project", "Description", tmp_path)

        captured = capsys.readouterr()
        assert "[OK] Task tracking found: KANBAN.md" in captured.out

    @patch("cli.resume_project_common.subprocess.run")
    @patch("cli.resume_project_common.check_claude_cli")
    def test_subprocess_called_with_correct_args(self, mock_check, mock_run, tmp_path):
        """Test that subprocess is called with correct arguments."""
        mock_check.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()

        resume_project("Project", "Description", tmp_path)

        # Verify subprocess.run was called
        assert mock_run.called
        call_args = mock_run.call_args

        # Check command includes "claude" and "cd"
        assert "claude" in call_args[0][0]
        assert "cd" in call_args[0][0][1]

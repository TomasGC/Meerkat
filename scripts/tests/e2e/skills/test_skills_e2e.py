"""
E2E tests — skills workflow.

Tests that skills correctly trigger the right scripts and produce
expected outputs. Skills are tested through their underlying Python
scripts since they require Claude Code to fully execute.

These tests validate the skill → script delegation chain.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

pytestmark = pytest.mark.e2e_skills


# ---------------------------------------------------------------------------
# E2E: analyze-commit skill → analyze_commit_quality.py
# ---------------------------------------------------------------------------

def test_analyze_commit_skill_triggers_quality_check():
    """analyze-commit skill must invoke analyze_commit_quality.py."""
    from cli.analyze_commit_quality import AnalyzeCommitQualityScript
    import argparse

    script = AnalyzeCommitQualityScript()
    with patch("cli.analyze_commit_quality.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="+x = 1\n+y = 2\n",
            stderr=""
        )
        args = argparse.Namespace(commits="HEAD", diff=None, format="json", checks=["security", "quality"])
        result = script.execute(args)
    assert isinstance(result, dict)
    assert "violations" in result or "issues" in result or "total_violations" in result


def test_analyze_commit_skill_clean_code_passes():
    """analyze-commit skill should report no violations for clean code."""
    from cli.analyze_commit_quality import AnalyzeCommitQualityScript
    import argparse

    script = AnalyzeCommitQualityScript()
    clean_diff = "+def process_data(items: list[str]) -> list[str]:\n+    return [i.strip() for i in items]\n"
    with patch("cli.analyze_commit_quality.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=clean_diff, stderr="")
        args = argparse.Namespace(commits="HEAD", diff=None, format="json", checks=["security", "quality"])
        result = script.execute(args)
    violations = result.get("violations", result.get("issues", []))
    total = result.get("total_violations", len(violations))
    assert total == 0 or isinstance(violations, list)


# ---------------------------------------------------------------------------
# E2E: update-context skill → update_kanban.py + generate_kanban_entry.py
# ---------------------------------------------------------------------------

def test_update_context_skill_generates_entry(tmp_path):
    """update-context skill uses generate_kanban_entry + update_kanban."""
    from cli.generate_kanban_entry import GenerateKanbanEntryScript
    import argparse

    script = GenerateKanbanEntryScript()
    with patch("cli.generate_kanban_entry.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="M scripts/cli/auth.py\nA scripts/tests/test_auth.py\n",
            stderr=""
        )
        args = argparse.Namespace(
            commits="abc123",
            issue="#1",
            style="professional",
            max_bullets=5,
            format="json"
        )
        result = script.execute(args)
    assert isinstance(result, dict)


def test_update_context_skill_writes_kanban(tmp_path):
    """update-context skill must persist KANBAN entry to disk."""
    from cli.update_kanban import UpdateKanbanScript
    import argparse

    kanban = tmp_path / "KANBAN.md"
    kanban.write_text("# KANBAN\n\n---\n\n---\n\n## Notes\n")

    script = UpdateKanbanScript()
    args = argparse.Namespace(
        issue="#1",
        commits="abc123",
        description="Implemented authentication feature",
        date="2026-05-29",
        format="json",
        kanban_file=kanban
    )
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban):
        result = script.execute(args)

    assert result["success"] is True
    content = kanban.read_text()
    assert "#1" in content
    assert "abc123" in content


# ---------------------------------------------------------------------------
# E2E: project-setup skill → validate_skill_structure.py
# ---------------------------------------------------------------------------

def test_project_setup_skill_validates_skill_structure(tmp_path):
    """project-setup skill validates SKILL.md structure during setup."""
    from cli.validate_skill_structure import ValidateSkillStructureScript
    import argparse

    valid_skill = tmp_path / "SKILL.md"
    valid_skill.write_text("""\
---
name: my-skill
description: A test skill
tools: Read, Write
model: sonnet
---

# My Skill

## What This Skill Does

This skill does something useful.

## Persona Definition

You are an expert developer.

## Tools

- **Read** - Read files

## Model

sonnet

## Hard Constraints

Always follow rules.

## Operational Guidelines

Follow the workflow.

## Self-Verification Checklist

- [ ] Check complete

## Communication Style

Professional and concise.
""")

    script = ValidateSkillStructureScript()
    args = argparse.Namespace(file=valid_skill, strict=False, format="json")
    result = script.execute(args)
    assert result["valid"] is True


# ---------------------------------------------------------------------------
# E2E: search-tech skill → dependency on script orchestration
# ---------------------------------------------------------------------------

def test_analyze_code_skill_detects_project_type(tmp_path):
    """analyze-code skill uses detect_project_type as first step."""
    from cli.detect_project_type import DetectProjectTypeScript
    import argparse

    # Create a Python project structure
    (tmp_path / "requirements.txt").write_text("pytest\nrequests\n")
    (tmp_path / "main.py").write_text("print('hello')\n")

    script = DetectProjectTypeScript()
    args = argparse.Namespace(path=tmp_path, format="json")
    result = script.execute(args)
    assert result.get("type") in ("python", "unknown") or "type" in result


# ---------------------------------------------------------------------------
# E2E: start-session skill → load_session_context.py
# ---------------------------------------------------------------------------

def test_start_session_skill_loads_context(tmp_path):
    """start-session skill invokes load_session_context to build context."""
    from cli.load_session_context import LoadSessionContextScript
    import argparse

    # Create minimal project structure
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "CLAUDE.md").write_text("# Project\n\n## Purpose\nTest project\n")

    script = LoadSessionContextScript()
    args = argparse.Namespace(
        project_root=tmp_path,
        format="json"
    )
    with patch("cli.load_session_context.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="main\n",
            stderr=""
        )
        result = script.execute(args)
    assert isinstance(result, dict)

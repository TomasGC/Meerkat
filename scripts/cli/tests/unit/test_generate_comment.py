#!/usr/bin/env python3
"""Tests for generate_comment.py"""

import argparse
from unittest.mock import patch

import pytest

from cli.generate_comment import (
    GenerateCommentScript,
    categorize_file,
    generate_implementation_details,
    generate_summary,
    get_base_branch,
    get_commit_files,
    get_commit_message,
    get_commits_in_range,
    get_current_branch,
)


def test_categorize_file_testing():
    """Test categorizing test files."""
    assert categorize_file("test_module.py") == "testing"
    assert categorize_file("module.test.ts") == "testing"
    assert categorize_file("module.spec.js") == "testing"
    assert categorize_file("tests/test_file.py") == "testing"
    assert categorize_file("fixtures/data.json") == "testing"


def test_categorize_file_scripts():
    """Test categorizing script files."""
    assert categorize_file("script.ps1") == "scripts"
    assert categorize_file("script.sh") == "scripts"
    assert categorize_file("scripts/utility.bash") == "scripts"


def test_categorize_file_scripts_exclude_tests():
    """Test that test scripts are not categorized as scripts."""
    assert categorize_file("script.Tests.ps1") == "testing"


def test_categorize_file_standards():
    """Test categorizing standards files."""
    assert categorize_file("rules/standards-code-quality.md") == "standards"
    assert categorize_file("standards-security.md") == "standards"
    assert categorize_file("coding-standards/README.md") == "standards"


def test_categorize_file_skills():
    """Test categorizing skills files."""
    assert categorize_file("skills/start-session.md") == "skills"
    assert categorize_file("skills/project-setup/SKILL.md") == "skills"


def test_categorize_file_agents():
    """Test categorizing agents files."""
    assert categorize_file("agents/code-reviewer/AGENT.md") == "agents"
    assert categorize_file("agents/analyzer.md") == "agents"


def test_categorize_file_documentation():
    """Test categorizing documentation files."""
    assert categorize_file("README.md") == "documentation"
    assert categorize_file("docs/guide.md") == "documentation"
    assert categorize_file("documentation/api.md") == "documentation"


def test_categorize_file_documentation_exclude():
    """Test excluding certain markdown files."""
    assert categorize_file("CHANGELOG.md") == "code"
    assert categorize_file("LICENSE.md") == "code"


def test_categorize_file_infrastructure():
    """Test categorizing infrastructure files."""
    assert categorize_file("Dockerfile") == "infrastructure"
    assert categorize_file("docker-compose.yml") == "infrastructure"
    assert categorize_file(".gitlab-ci.yml") == "infrastructure"
    assert categorize_file(".github/workflows/ci.yml") == "infrastructure"
    assert categorize_file("k8s/deployment.yaml") == "infrastructure"
    assert categorize_file("terraform/main.tf") == "infrastructure"


def test_categorize_file_configuration():
    """Test categorizing configuration files."""
    assert categorize_file("config.json") == "configuration"
    assert categorize_file("settings.yaml") == "configuration"
    assert categorize_file("app.toml") == "configuration"
    assert categorize_file("app.config") == "configuration"


def test_categorize_file_configuration_exclude():
    """Test excluding package-lock.json."""
    assert categorize_file("package-lock.json") == "code"


def test_categorize_file_code_fallback():
    """Test fallback to code category."""
    assert categorize_file("src/module.py") == "code"
    assert categorize_file("src/component.tsx") == "code"
    assert categorize_file("main.go") == "code"


def test_generate_summary_testing():
    """Test generating summary with testing."""
    categories = {"testing": 10}
    summary = generate_summary(categories)
    assert "comprehensive test suite" in summary


def test_generate_summary_scripts():
    """Test generating summary with scripts."""
    categories = {"scripts": 5}
    summary = generate_summary(categories)
    assert "utility scripts" in summary


def test_generate_summary_multiple():
    """Test generating summary with multiple categories."""
    categories = {"testing": 10, "scripts": 5, "documentation": 3}
    summary = generate_summary(categories)
    assert "test suite" in summary or "scripts" in summary or "documentation" in summary


def test_generate_summary_empty():
    """Test generating summary with no categories."""
    categories = {}
    summary = generate_summary(categories)
    assert summary == "project updates"


def test_generate_implementation_details_testing():
    """Test generating details for testing."""
    categories = {"testing": 10}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Test Suite:" in text
    assert "10 files" in text


def test_generate_implementation_details_scripts():
    """Test generating details for scripts."""
    categories = {"scripts": 5}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Utility Scripts:" in text
    assert "5 files" in text


def test_generate_implementation_details_standards():
    """Test generating details for standards."""
    categories = {"standards": 3}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Coding Standards:" in text
    assert "3 files" in text


def test_generate_implementation_details_skills():
    """Test generating details for skills."""
    categories = {"skills": 4}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Custom Skills:" in text
    assert "4 files" in text


def test_generate_implementation_details_infrastructure():
    """Test generating details for infrastructure."""
    categories = {"infrastructure": 2}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Infrastructure:" in text
    assert "2 files" in text


def test_generate_implementation_details_documentation():
    """Test generating details for documentation."""
    categories = {"documentation": 6}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Documentation:" in text
    assert "6 files" in text


def test_generate_implementation_details_code():
    """Test generating details for code."""
    categories = {"code": 15}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Code:" in text
    assert "15 files" in text


def test_generate_implementation_details_multiple():
    """Test generating details for multiple categories."""
    categories = {"testing": 10, "scripts": 5, "code": 15}
    details = generate_implementation_details(categories)

    text = "\n".join(details)
    assert "Code:" in text
    assert "Test Suite:" in text
    assert "Utility Scripts:" in text


def test_generate_implementation_details_empty():
    """Test generating details with no categories."""
    categories = {}
    details = generate_implementation_details(categories)

    assert details == []


# ── git helpers and script (run_command mocked) ──────────────────────────────

C1 = "1111111aaaa"
C2 = "2222222bbbb"

_REPO = {
    ("git", "branch", "--show-current"): (0, "feature/x\n", ""),
    ("git", "rev-parse", "--verify", "main"): (1, "", ""),
    ("git", "rev-parse", "--verify", "master"): (0, "abc\n", ""),
    ("git", "merge-base", "master", "feature/x"): (0, "base123\n", ""),
    ("git", "rev-list", "base123..feature/x"): (0, f"{C1}\n{C2}\n", ""),
    ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", C1): (0, "src/app.py\ntests/test_app.py\n", ""),
    ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", C2): (0, "README.md\n", ""),
    ("git", "log", "-1", "--format=%s", C1): (0, "feat: add app\n", ""),
    ("git", "log", "-1", "--format=%s", C2): (0, "docs: readme\n", ""),
}


def _git(responses=None):
    table = dict(_REPO if responses is None else responses)
    return lambda cmd, **_kw: table.get(tuple(cmd), (1, "", "fail"))


def _execute(**kwargs):
    args = argparse.Namespace(**{"commits": "", "auto": False, "base_branch": "", "style": "detailed", **kwargs})
    with patch("cli.generate_comment.run_command", side_effect=_git()):
        return GenerateCommentScript().execute(args)


def test_get_current_branch_outside_repo_raises():
    with patch("cli.generate_comment.run_command", return_value=(128, "", "")):
        with pytest.raises(RuntimeError, match="Not a git repository"):
            get_current_branch()


def test_get_base_branch_picks_first_existing():
    with patch("cli.generate_comment.run_command", side_effect=_git()):
        assert get_base_branch() == "master"


def test_get_base_branch_defaults_to_main():
    with patch("cli.generate_comment.run_command", return_value=(1, "", "")):
        assert get_base_branch() == "main"


def test_get_commits_in_range_lists_commits_since_merge_base():
    with patch("cli.generate_comment.run_command", side_effect=_git()):
        assert get_commits_in_range("master", "feature/x") == [C1, C2]


def test_get_commits_in_range_without_merge_base_raises():
    with patch("cli.generate_comment.run_command", side_effect=_git({})):
        with pytest.raises(RuntimeError, match="merge base with main"):
            get_commits_in_range("main", "feature/x")


def test_get_commits_in_range_rev_list_failure_raises():
    responses = {("git", "merge-base", "main", "f"): (0, "b\n", "")}
    with patch("cli.generate_comment.run_command", side_effect=_git(responses)):
        with pytest.raises(RuntimeError, match="Failed to get commits"):
            get_commits_in_range("main", "f")


def test_commit_files_and_message_empty_on_git_failure():
    with patch("cli.generate_comment.run_command", return_value=(1, "", "")):
        assert get_commit_files("x") == []
        assert get_commit_message("x") == ""


def test_execute_requires_auto_or_commits():
    assert _execute() == {"success": False, "error": "Either --auto or --commits must be specified"}


def test_execute_auto_detailed_comment():
    result = _execute(auto=True)

    assert result["success"] is True
    assert (result["commits"], result["files"]) == (2, 3)
    assert result["categories"] == {"code": 1, "testing": 1, "documentation": 1}
    comment = result["comment"]
    assert comment.startswith("Work Summary: comprehensive test suite, documentation, code implementation")
    assert "Statistics: 3 files modified across 2 commits" in comment
    assert "- 1111111: feat: add app" in comment
    assert "- 2222222: docs: readme" in comment


def test_execute_explicit_commits_summary_style():
    result = _execute(commits=f"{C1}, {C2}", style="summary")
    assert result["comment"] == (
        "Work completed: comprehensive test suite, documentation, code implementation\n\n"
        "Files modified: 3 across 2 commits"
    )


def test_execute_technical_style_lists_details_only():
    result = _execute(commits=C2, style="technical")
    assert result["comment"] == "Implementation Details:\n- Documentation: 1 files"


def test_execute_with_no_commits_on_branch():
    responses = dict(_REPO)
    responses[("git", "rev-list", "base123..feature/x")] = (0, "", "")
    args = argparse.Namespace(commits="", auto=True, base_branch="master", style="detailed")
    with patch("cli.generate_comment.run_command", side_effect=_git(responses)):
        assert GenerateCommentScript().execute(args) == {"success": True, "comment": "No commits to analyze."}


def test_execute_git_error_is_reported():
    args = argparse.Namespace(commits="", auto=True, base_branch="", style="detailed")
    with patch("cli.generate_comment.run_command", return_value=(128, "", "")):
        result = GenerateCommentScript().execute(args)
    assert result == {"success": False, "error": "Not a git repository"}


def test_run_text_and_summary_formats(capsys):
    with patch("cli.generate_comment.run_command", side_effect=_git()):
        GenerateCommentScript().run(["--commits", C2, "--style", "technical", "--format", "text"])
        GenerateCommentScript().run(["--commits", C2, "--format", "summary"])
    out = capsys.readouterr().out.splitlines()
    assert out == [
        "Implementation Details:",
        "- Documentation: 1 files",
        "Generated comment for 1 commits, 1 files",
    ]


def test_error_result_formats():
    script = GenerateCommentScript()
    assert script.format_text({"success": False, "error": "x"}) == "Error: x"
    assert script.format_summary({"success": False, "error": "x"}) == "[ERROR] x"


def test_generate_summary_names_every_category():
    categories = dict.fromkeys(
        ["standards", "skills", "agents", "infrastructure", "configuration"],
        1,
    )
    assert generate_summary(categories) == (
        "coding standards, custom skills, agents, infrastructure changes, configuration updates"
    )

"""Tests for validate_markdown.py — markdown format compliance validator."""

import json
from pathlib import Path

import pytest

from cli.validate_markdown import ValidateMarkdownScript

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def script():
    return ValidateMarkdownScript()

@pytest.fixture
def kanban_file(tmp_path: Path) -> Path:
    f = tmp_path / "KANBAN.md"
    f.write_text("# KANBAN\n\n## TODO\n\n## IN PROGRESS\n\n## DONE\n\n2024-01-15 - Entry\n")
    return f

@pytest.fixture
def architecture_file(tmp_path: Path) -> Path:
    f = tmp_path / "ARCHITECTURE.md"
    f.write_text("# Architecture\n\n## Components\n\nThis describes the architecture component design layer.\n")
    return f

@pytest.fixture
def claude_file(tmp_path: Path) -> Path:
    f = tmp_path / "CLAUDE.md"
    f.write_text("# CLAUDE\n\n## Purpose\n\nInstructions for Claude Code usage.\n## Rules\n\n## Guidelines\n")
    return f

@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    f = tmp_path / "EMPTY.md"
    f.write_text("")
    return f

@pytest.fixture
def no_headings_file(tmp_path: Path) -> Path:
    f = tmp_path / "noheadings.md"
    f.write_text("This is content without any headings.\n")
    return f

# ---------------------------------------------------------------------------
# Unit: type detection
# ---------------------------------------------------------------------------

def test_detect_type_kanban(script, kanban_file):
    assert script._detect_type(kanban_file) == "kanban"

def test_detect_type_architecture(script, architecture_file):
    assert script._detect_type(architecture_file) == "architecture"

def test_detect_type_claude(script, claude_file):
    assert script._detect_type(claude_file) == "claude"

def test_detect_type_generic(script, tmp_path):
    f = tmp_path / "README.md"
    f.write_text("")
    assert script._detect_type(f) == "generic"

# ---------------------------------------------------------------------------
# Unit: structure checks
# ---------------------------------------------------------------------------

def test_check_structure_with_headings(script):
    errors, warnings, info = [], [], []
    script._check_structure("# Title\n\n## Section\n\nContent\n", errors, warnings, info)
    assert not errors
    assert any("heading" in i.lower() for i in info)

def test_check_structure_no_headings(script):
    errors, warnings, info = [], [], []
    script._check_structure("Just some text without headings.\n", errors, warnings, info)
    assert any("heading" in w.lower() for w in warnings)

def test_check_structure_empty_file(script):
    errors, warnings, info = [], [], []
    script._check_structure("", errors, warnings, info)
    assert any("empty" in e.lower() for e in errors)

# ---------------------------------------------------------------------------
# Unit: encoding checks
# ---------------------------------------------------------------------------

def test_check_encoding_ascii(script):
    errors, warnings, info = [], [], []
    script._check_encoding("Hello world", errors, warnings, info)
    assert any("ASCII" in i for i in info)

def test_check_encoding_utf8(script):
    errors, warnings, info = [], [], []
    script._check_encoding("Hello — world", errors, warnings, info)
    assert any("UTF-8" in i for i in info)

# ---------------------------------------------------------------------------
# Unit: KANBAN checks
# ---------------------------------------------------------------------------

def test_check_kanban_with_all_sections(script):
    content = "# KANBAN\n\n## TODO\n\n## IN PROGRESS\n\n## DONE\n\n2024-01-15 - Entry\n"
    errors, warnings, info = [], [], []
    script._check_kanban(content, errors, warnings, info)
    assert not [w for w in warnings if "Missing" in w]

def test_check_kanban_missing_sections(script):
    content = "# KANBAN\n\nSome content without sections.\n"
    errors, warnings, info = [], [], []
    script._check_kanban(content, errors, warnings, info)
    assert len(warnings) > 0

def test_check_kanban_no_dates(script):
    content = "# KANBAN\n\n## TODO\n## IN PROGRESS\n## DONE\n"
    errors, warnings, info = [], [], []
    script._check_kanban(content, errors, warnings, info)
    assert any("date" in w.lower() for w in warnings)

def test_check_kanban_with_dates(script):
    content = "# KANBAN\n\n## TODO\n## IN PROGRESS\n## DONE\n\n2024-01-15 - Some entry\n"
    errors, warnings, info = [], [], []
    script._check_kanban(content, errors, warnings, info)
    assert not any("date" in w.lower() for w in warnings)

# ---------------------------------------------------------------------------
# Unit: ARCHITECTURE checks
# ---------------------------------------------------------------------------

def test_check_architecture_with_keywords(script):
    content = "# Architecture\n\nThis describes the component design layer module.\n"
    errors, warnings, info = [], [], []
    script._check_architecture(content, errors, warnings, info)
    assert not [w for w in warnings if "keyword" in w.lower()]

def test_check_architecture_no_keywords(script):
    content = "# My File\n\nSome random text here.\n"
    errors, warnings, info = [], [], []
    script._check_architecture(content, errors, warnings, info)
    assert any("keyword" in w.lower() for w in warnings)

# ---------------------------------------------------------------------------
# Unit: CLAUDE checks
# ---------------------------------------------------------------------------

def test_check_claude_with_sections(script):
    content = "# CLAUDE\n\n## Purpose\n\nSome text.\n## Rules\n"
    errors, warnings, info = [], [], []
    script._check_claude(content, errors, warnings, info)
    assert not [w for w in warnings if "section" in w.lower()]

def test_check_claude_no_sections(script):
    content = "# CLAUDE\n\nSome random text.\n"
    errors, warnings, info = [], [], []
    script._check_claude(content, errors, warnings, info)
    assert any("section" in w.lower() for w in warnings)

def test_check_claude_no_english(script):
    content = "---\n123 456 789\n"
    errors, warnings, info = [], [], []
    script._check_claude(content, errors, warnings, info)
    assert any("English" in w for w in warnings)

# ---------------------------------------------------------------------------
# Unit: full validation
# ---------------------------------------------------------------------------

def test_validate_kanban_valid(script, kanban_file):
    errors, warnings, info = script._validate(kanban_file, "kanban")
    assert not errors

def test_validate_architecture_valid(script, architecture_file):
    errors, warnings, info = script._validate(architecture_file, "architecture")
    assert not errors

def test_validate_empty_file(script, empty_file):
    errors, warnings, info = script._validate(empty_file, "generic")
    assert any("empty" in e.lower() for e in errors)

# ---------------------------------------------------------------------------
# Unit: strict mode
# ---------------------------------------------------------------------------

def test_execute_strict_mode_promotes_warnings(script, tmp_path):
    import argparse
    f = tmp_path / "test.md"
    f.write_text("# Title\n\nSome content without required sections.\n")
    args = argparse.Namespace(file=f, type="auto", strict=True)
    result = script.execute(args)
    # In strict mode, warnings become errors
    assert result["summary"]["warningCount"] == 0

def test_execute_normal_mode_keeps_warnings(script, tmp_path):
    import argparse
    f = tmp_path / "test.md"
    f.write_text("# Title\n\nSome content.\n")
    args = argparse.Namespace(file=f, type="generic", strict=False)
    result = script.execute(args)
    assert "valid" in result

def test_execute_file_not_found(script, tmp_path):
    import argparse
    args = argparse.Namespace(file=tmp_path / "missing.md", type="auto", strict=False)
    with pytest.raises(FileNotFoundError):
        script.execute(args)

# ---------------------------------------------------------------------------
# Unit: format methods
# ---------------------------------------------------------------------------

def test_format_text_valid(script):
    result = {
        "file": "/path/to/KANBAN.md",
        "type": "kanban",
        "valid": True,
        "errors": [],
        "warnings": [],
        "info": ["File is ASCII"],
        "summary": {"errorCount": 0, "warningCount": 0, "infoCount": 1}
    }
    text = script.format_text(result)
    assert "[OK]" in text

def test_format_text_invalid(script):
    result = {
        "file": "/path/to/test.md",
        "type": "generic",
        "valid": False,
        "errors": ["File is empty"],
        "warnings": [],
        "info": [],
        "summary": {"errorCount": 1, "warningCount": 0, "infoCount": 0}
    }
    text = script.format_text(result)
    assert "[FAIL]" in text
    assert "File is empty" in text

def test_format_summary(script):
    result = {
        "file": "/path/to/KANBAN.md",
        "type": "kanban",
        "valid": True,
        "summary": {"errorCount": 0, "warningCount": 1, "infoCount": 2}
    }
    summary = script.format_summary(result)
    assert "KANBAN.md" in summary
    assert "OK" in summary

# ---------------------------------------------------------------------------
# Integration: CLI run
# ---------------------------------------------------------------------------

def test_run_valid_kanban_file(tmp_path, capsys):
    f = tmp_path / "KANBAN.md"
    f.write_text("# KANBAN\n\n## TODO\n\n## IN PROGRESS\n\n## DONE\n\n2024-01-15 - Entry\n")
    script = ValidateMarkdownScript()
    exit_code = script.run(["--file", str(f), "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["type"] == "kanban"

def test_run_missing_file_exits(tmp_path):
    script = ValidateMarkdownScript()
    exit_code = script.run(["--file", str(tmp_path / "missing.md")])
    assert exit_code == 1

def test_run_text_format(tmp_path, capsys):
    f = tmp_path / "README.md"
    f.write_text("# README\n\nContent here.\n")
    script = ValidateMarkdownScript()
    exit_code = script.run(["--file", str(f), "--format", "text"])
    assert exit_code == 0

def test_run_explicit_type(tmp_path, capsys):
    f = tmp_path / "notes.md"
    f.write_text("# Architecture Overview\n\nComponent design description.\n")
    script = ValidateMarkdownScript()
    exit_code = script.run(["--file", str(f), "--type", "architecture", "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["type"] == "architecture"

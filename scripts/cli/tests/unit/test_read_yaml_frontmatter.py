#!/usr/bin/env python3
"""Tests for read_yaml_frontmatter.py"""

import argparse
import importlib.util
import json
from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import pytest

import cli.read_yaml_frontmatter as reader
from cli.read_yaml_frontmatter import ReadYamlFrontmatterScript, extract_frontmatter, parse_yaml_simple
from lib import paths
from lib.utils import write_file_safe


def test_extract_frontmatter_valid(tmp_path):
    """Test extracting valid YAML frontmatter."""
    content = dedent("""
        ---
        name: test-skill
        description: A test skill
        model: sonnet
        ---

        # Content here
    """).strip()

    file_path = tmp_path / "test.md"
    write_file_safe(file_path, content)

    frontmatter = extract_frontmatter(file_path)

    assert frontmatter is not None
    assert frontmatter["name"] == "test-skill"
    assert frontmatter["description"] == "A test skill"
    assert frontmatter["model"] == "sonnet"


def test_extract_frontmatter_missing(tmp_path):
    """Test extraction when no frontmatter present."""
    content = "# Just content, no frontmatter"

    file_path = tmp_path / "no-frontmatter.md"
    write_file_safe(file_path, content)

    frontmatter = extract_frontmatter(file_path)

    assert frontmatter is None


def test_extract_frontmatter_multiline(tmp_path):
    """Test extracting multiline YAML frontmatter."""
    content = dedent("""
        ---
        name: multiline-test
        description: |
          This is a multiline
          description with
          several lines
        tools: [Read, Write, Edit]
        ---

        # Content
    """).strip()

    file_path = tmp_path / "multiline.md"
    write_file_safe(file_path, content)

    frontmatter = extract_frontmatter(file_path)

    assert frontmatter is not None
    assert frontmatter["name"] == "multiline-test"
    assert "multiline" in frontmatter["description"]
    assert isinstance(frontmatter["tools"], list)
    assert len(frontmatter["tools"]) == 3


def test_extract_frontmatter_nonexistent_file():
    """Test extraction with nonexistent file."""
    frontmatter = extract_frontmatter(Path("/nonexistent/file.md"))

    assert frontmatter is None


def test_parse_yaml_simple_basic():
    """Test simple YAML parser with basic key-value."""
    yaml_content = "name: test-skill\ndescription: A test"

    parsed = parse_yaml_simple(yaml_content)

    assert parsed["name"] == "test-skill"
    assert parsed["description"] == "A test"


def test_parse_yaml_simple_array():
    """Test simple YAML parser with array."""
    yaml_content = "tools: [Read, Write, Edit]"

    parsed = parse_yaml_simple(yaml_content)

    assert "tools" in parsed
    assert isinstance(parsed["tools"], list)
    assert len(parsed["tools"]) == 3
    assert "Read" in parsed["tools"]


def test_parse_yaml_simple_multiline():
    """Test simple YAML parser with multiline string."""
    yaml_content = dedent("""
        description: |
          Line 1
          Line 2
          Line 3
    """).strip()

    parsed = parse_yaml_simple(yaml_content)

    assert "description" in parsed
    assert "Line 1" in parsed["description"]
    assert "Line 2" in parsed["description"]


def test_parse_yaml_simple_quoted():
    """Test simple YAML parser with quoted string."""
    yaml_content = 'name: "quoted-name"'

    parsed = parse_yaml_simple(yaml_content)

    assert parsed["name"] == "quoted-name"


def test_parse_yaml_simple_empty_value():
    """Test simple YAML parser with empty value."""
    yaml_content = "name:\ndescription: test"

    parsed = parse_yaml_simple(yaml_content)

    assert "name" in parsed
    assert parsed["name"] is None
    assert parsed["description"] == "test"


def test_extract_frontmatter_real_skill_file():
    """Test extraction with real skill file (if available)."""
    # Look for a real skill file
    skill_dirs = paths.CHECKOUT / "skills"

    if not skill_dirs.exists():
        pytest.skip("No skills directory found")

    skill_files = list(skill_dirs.rglob("SKILL.md"))

    if not skill_files:
        pytest.skip("No SKILL.md files found")

    # Test with first found skill
    frontmatter = extract_frontmatter(skill_files[0])

    assert frontmatter is not None
    assert "name" in frontmatter
    assert "description" in frontmatter


def test_extract_frontmatter_complex_yaml(tmp_path):
    """Test extraction with complex YAML structure."""
    content = dedent("""
        ---
        name: complex-skill
        description: Test description
        tools:
          - Read
          - Write
          - Edit
        model: sonnet
        metadata:
          version: 1.0.0
          author: test
        ---

        # Content
    """).strip()

    file_path = tmp_path / "complex.md"
    write_file_safe(file_path, content)

    frontmatter = extract_frontmatter(file_path)

    assert frontmatter is not None
    assert frontmatter["name"] == "complex-skill"

    # Nested structures are parsed only with PyYAML; the simple fallback parser may flatten them
    if importlib.util.find_spec("yaml") is not None:
        assert isinstance(frontmatter.get("tools"), list)
        assert isinstance(frontmatter.get("metadata"), dict)


def test_extract_frontmatter_windows_line_endings(tmp_path):
    """Test extraction with Windows line endings (CRLF)."""
    content = "---\r\nname: windows-test\r\ndescription: Test\r\n---\r\n\r\n# Content"

    file_path = tmp_path / "windows.md"
    file_path.write_text(content, encoding="utf-8")

    frontmatter = extract_frontmatter(file_path)

    assert frontmatter is not None
    assert frontmatter["name"] == "windows-test"


# ── fallback parser branches, YAML errors and the script ─────────────────────


def test_parse_yaml_simple_single_quotes_and_folded_block_then_key():
    parsed = parse_yaml_simple("title: 'x'\nbody: >\n  first\nunindented\nnext: y")
    assert parsed == {"title": "x", "body": "first\nunindented", "next": "y"}


def test_extract_frontmatter_without_pyyaml_uses_simple_parser(tmp_path):
    file_path = tmp_path / "s.md"
    file_path.write_text("---\nname: s\ntools: [A, B]\n---\n", encoding="utf-8")
    with patch.object(reader, "YAML_AVAILABLE", False):
        assert extract_frontmatter(file_path) == {"name": "s", "tools": ["A", "B"]}


def test_extract_frontmatter_non_mapping_yaml_is_empty_dict(tmp_path):
    file_path = tmp_path / "l.md"
    file_path.write_text("---\n- a\n- b\n---\n", encoding="utf-8")
    assert extract_frontmatter(file_path) == {}


def test_extract_frontmatter_invalid_yaml_raises(tmp_path):
    file_path = tmp_path / "bad.md"
    file_path.write_text("---\nname: [unclosed\n---\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Failed to parse YAML"):
        extract_frontmatter(file_path)


@pytest.fixture
def skill_file(tmp_path):
    file_path = tmp_path / "SKILL.md"
    file_path.write_text(
        "---\nname: demo\ntools: [Read, Bash]\ndescription: |\n  line one\n  line two\n---\n# Body\n",
        encoding="utf-8",
    )
    return file_path


def _run(argv, capsys):
    code = ReadYamlFrontmatterScript().run(argv)
    return code, capsys.readouterr().out


def test_run_json_output(skill_file, capsys):
    code, out = _run(["--file", str(skill_file)], capsys)
    assert code == 0
    data = json.loads(out)
    assert data["frontmatter"] == {"name": "demo", "tools": ["Read", "Bash"], "description": "line one\nline two"}
    assert data["format_yaml"] is False


def test_run_text_output(skill_file, capsys):
    _, out = _run(["--file", str(skill_file), "--format", "text"], capsys)
    assert out.splitlines() == ["name: demo", "tools: Read, Bash", "description:", "  line one", "  line two"]


def test_run_summary_output(skill_file, capsys):
    _, out = _run(["--file", str(skill_file), "--format", "summary"], capsys)
    assert out.strip() == "Extracted 3 fields: name, tools, description"


def test_run_format_yaml_flag(skill_file, capsys):
    _, out = _run(["--file", str(skill_file), "--format-yaml"], capsys)
    assert out.startswith("description: 'line one\n")
    assert "name: demo\ntools:\n- Read\n- Bash\n" in out


def test_execute_reports_yaml_error(tmp_path):
    file_path = tmp_path / "bad.md"
    file_path.write_text("---\nname: [unclosed\n---\n", encoding="utf-8")
    result = ReadYamlFrontmatterScript().execute(argparse.Namespace(file=file_path, format_yaml=False))
    assert result["success"] is False
    assert result["error"].startswith("Failed to parse YAML")


def test_error_result_formats():
    script = ReadYamlFrontmatterScript()
    assert script.format_text({"success": False, "error": "x"}) == "Error: x"
    assert script.format_summary({"success": False, "error": "x"}) == "[ERROR] x"


def test_run_text_output_for_file_without_frontmatter(tmp_path, capsys):
    file_path = tmp_path / "plain.md"
    file_path.write_text("# no frontmatter\n", encoding="utf-8")
    code, out = _run(["--file", str(file_path), "--format", "text"], capsys)
    assert code == 0
    assert out.strip() == "No frontmatter found"


def test_horizontal_rules_further_down_are_not_frontmatter(tmp_path, capsys):
    file_path = tmp_path / "readme.md"
    file_path.write_text("# Title\n\n---\n\nname: not a field\n\n---\n\nMore text\n", encoding="utf-8")
    assert extract_frontmatter(file_path) is None
    code, out = _run(["--file", str(file_path), "--format", "text"], capsys)
    assert code == 0
    assert out.strip() == "No frontmatter found"


def test_crlf_frontmatter_is_parsed(tmp_path):
    file_path = tmp_path / "skill.md"
    file_path.write_bytes(b"---\r\nname: crlf-skill\r\nmodel: sonnet\r\n---\r\n# Body\r\n")
    assert extract_frontmatter(file_path) == {"name": "crlf-skill", "model": "sonnet"}


def test_closing_delimiter_must_be_a_line_of_its_own(tmp_path):
    file_path = tmp_path / "skill.md"
    file_path.write_text("---\nname: x\n---not-a-delimiter\nmore: y\n", encoding="utf-8")
    assert extract_frontmatter(file_path) is None


def test_run_summary_output_for_file_without_frontmatter(tmp_path, capsys):
    file_path = tmp_path / "plain.md"
    file_path.write_text("# no frontmatter\n", encoding="utf-8")
    code, out = _run(["--file", str(file_path), "--format", "summary"], capsys)
    assert code == 0
    assert out.strip() == "No frontmatter found"

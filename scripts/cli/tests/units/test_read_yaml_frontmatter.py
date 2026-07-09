#!/usr/bin/env python3
"""Tests for read_yaml_frontmatter.py"""

from pathlib import Path
from textwrap import dedent

import pytest

from cli.read_yaml_frontmatter import extract_frontmatter, parse_yaml_simple
from common.utils import write_file_safe

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
    skill_dirs = Path.home() / ".claude" / "skills"

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

    try:
        # If PyYAML available, check nested structure
        import yaml
        assert isinstance(frontmatter.get("tools"), list)
        assert isinstance(frontmatter.get("metadata"), dict)
    except ImportError:
        # Simple parser may not handle nested structures
        pass

def test_extract_frontmatter_windows_line_endings(tmp_path):
    """Test extraction with Windows line endings (CRLF)."""
    content = "---\r\nname: windows-test\r\ndescription: Test\r\n---\r\n\r\n# Content"

    file_path = tmp_path / "windows.md"
    file_path.write_text(content, encoding="utf-8")

    frontmatter = extract_frontmatter(file_path)

    assert frontmatter is not None
    assert frontmatter["name"] == "windows-test"

#!/usr/bin/env python3
"""Tests for update_section_in_markdown.py"""

from pathlib import Path

import pytest

from cli.update_section_in_markdown import update_section_in_markdown
from common.utils import write_file_safe

@pytest.fixture
def sample_markdown(tmp_path):
    """Create a sample markdown file."""
    content = """# Project Documentation

## Introduction

This is the introduction section.
It has multiple lines.

## Architecture

Current architecture description.
Some more details here.

## Installation

Steps to install:
1. Clone repo
2. Install dependencies

## Usage

How to use the project.

## License

MIT License
"""
    md_file = tmp_path / "README.md"
    write_file_safe(md_file, content)
    return md_file

@pytest.fixture
def numbered_sections_markdown(tmp_path):
    """Create markdown with numbered sections."""
    content = """# Guide

1. **Introduction**

This is section 1.
With some content.

2. **Setup**

This is section 2.
More content here.

3. **Advanced Topics**

This is section 3.
Additional details.

4. **Conclusion**

Final section.
"""
    md_file = tmp_path / "GUIDE.md"
    write_file_safe(md_file, content)
    return md_file

def test_update_header_section(sample_markdown):
    """Test updating a header-based section."""
    new_content = "New architecture information.\nWith multiple lines."

    result = update_section_in_markdown(
        sample_markdown,
        "## Architecture",
        new_content,
        create_backup=False
    )

    assert result["updated"] is True
    assert result["section"] == "## Architecture"
    assert result["backup"] is None

    # Verify updated content
    updated = sample_markdown.read_text()
    assert "New architecture information." in updated
    assert "With multiple lines." in updated
    assert "Current architecture description." not in updated

def test_update_numbered_section(numbered_sections_markdown):
    """Test updating a numbered section."""
    new_content = "Updated section 2 content.\nCompletely new."

    result = update_section_in_markdown(
        numbered_sections_markdown,
        "2. **Setup**",
        new_content,
        create_backup=False
    )

    assert result["updated"] is True

    # Verify updated content
    updated = numbered_sections_markdown.read_text()
    assert "Updated section 2 content." in updated
    assert "Completely new." in updated
    assert "This is section 2." not in updated

def test_update_with_backup(sample_markdown):
    """Test updating with backup creation."""
    new_content = "New installation steps."

    result = update_section_in_markdown(
        sample_markdown,
        "## Installation",
        new_content,
        create_backup=True
    )

    assert result["updated"] is True
    assert result["backup"] is not None

    # Verify backup exists
    backup_path = Path(result["backup"])
    assert backup_path.exists()

    # Verify backup contains original content
    backup_content = backup_path.read_text()
    assert "Steps to install:" in backup_content

def test_update_first_section(sample_markdown):
    """Test updating the first section."""
    new_content = "New introduction text.\nUpdated content."

    result = update_section_in_markdown(
        sample_markdown,
        "## Introduction",
        new_content,
        create_backup=False
    )

    assert result["updated"] is True

    updated = sample_markdown.read_text()
    assert "New introduction text." in updated
    assert "This is the introduction section." not in updated

def test_update_last_section(sample_markdown):
    """Test updating the last section."""
    new_content = "Apache License 2.0"

    result = update_section_in_markdown(
        sample_markdown,
        "## License",
        new_content,
        create_backup=False
    )

    assert result["updated"] is True

    updated = sample_markdown.read_text()
    assert "Apache License 2.0" in updated
    assert "MIT License" not in updated

def test_update_preserves_other_sections(sample_markdown):
    """Test that updating one section preserves others."""
    original = sample_markdown.read_text()

    new_content = "Updated architecture."

    update_section_in_markdown(
        sample_markdown,
        "## Architecture",
        new_content,
        create_backup=False
    )

    updated = sample_markdown.read_text()

    # Other sections should be preserved
    assert "## Introduction" in updated
    assert "This is the introduction section." in updated
    assert "## Installation" in updated
    assert "Steps to install:" in updated
    assert "## Usage" in updated
    assert "## License" in updated

def test_update_section_not_found(sample_markdown):
    """Test error when section not found."""
    with pytest.raises(ValueError, match="Section not found"):
        update_section_in_markdown(
            sample_markdown,
            "## Nonexistent Section",
            "content",
            create_backup=False
        )

def test_update_nonexistent_file(tmp_path):
    """Test error when file doesn't exist."""
    nonexistent = tmp_path / "nonexistent.md"

    with pytest.raises(FileNotFoundError, match="File not found"):
        update_section_in_markdown(
            nonexistent,
            "## Section",
            "content",
            create_backup=False
        )

def test_update_lines_changed_increase(sample_markdown):
    """Test lines changed calculation when adding lines."""
    original_lines = len(sample_markdown.read_text().split("\n"))

    new_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"

    result = update_section_in_markdown(
        sample_markdown,
        "## Architecture",
        new_content,
        create_backup=False
    )

    # Should have added lines
    assert result["linesChanged"] > 0

def test_update_lines_changed_decrease(sample_markdown):
    """Test lines changed calculation when removing lines."""
    original_lines = len(sample_markdown.read_text().split("\n"))

    new_content = "Short"

    result = update_section_in_markdown(
        sample_markdown,
        "## Installation",
        new_content,
        create_backup=False
    )

    # Should have removed lines
    assert result["linesChanged"] < 0

def test_update_section_with_special_characters(tmp_path):
    """Test updating section with special regex characters."""
    content = """# Guide

## Section (with parens)

Original content.

## Next Section

Other content.
"""
    md_file = tmp_path / "test.md"
    write_file_safe(md_file, content)

    new_content = "Updated content."

    result = update_section_in_markdown(
        md_file,
        "## Section (with parens)",
        new_content,
        create_backup=False
    )

    assert result["updated"] is True

    updated = md_file.read_text()
    assert "Updated content." in updated
    assert "Original content." not in updated

def test_update_section_with_asterisks(numbered_sections_markdown):
    """Test updating section with asterisks (bold markdown)."""
    new_content = "Updated introduction."

    result = update_section_in_markdown(
        numbered_sections_markdown,
        "1. **Introduction**",
        new_content,
        create_backup=False
    )

    assert result["updated"] is True

    updated = numbered_sections_markdown.read_text()
    assert "Updated introduction." in updated

def test_update_nested_headers(tmp_path):
    """Test updating section with nested headers."""
    content = """# Main

## Section A

Content A.

### Subsection A1

Subsection content.

## Section B

Content B.
"""
    md_file = tmp_path / "nested.md"
    write_file_safe(md_file, content)

    new_content = "Updated A.\n\n### New Subsection\n\nNew content."

    result = update_section_in_markdown(
        md_file,
        "## Section A",
        new_content,
        create_backup=False
    )

    assert result["updated"] is True

    updated = md_file.read_text()
    assert "Updated A." in updated
    assert "New Subsection" in updated
    assert "Subsection A1" not in updated
    # Section B should be preserved
    assert "## Section B" in updated
    assert "Content B." in updated

def test_backup_filename_format(sample_markdown):
    """Test backup filename format."""
    result = update_section_in_markdown(
        sample_markdown,
        "## Architecture",
        "New content",
        create_backup=True
    )

    backup_path = Path(result["backup"])

    # Should have format: filename.backup.YYYYMMDD-HHMMSS.ext
    assert ".backup." in backup_path.name
    assert backup_path.suffix == ".md"

def test_update_empty_section_content(sample_markdown):
    """Test updating section with empty content."""
    result = update_section_in_markdown(
        sample_markdown,
        "## Architecture",
        "",
        create_backup=False
    )

    assert result["updated"] is True

    updated = sample_markdown.read_text()
    # Section header should remain, but content should be empty
    assert "## Architecture" in updated

def test_update_preserves_line_endings(tmp_path):
    """Test that line endings are preserved."""
    content = "# Title\n\n## Section\n\nContent\n"
    md_file = tmp_path / "test.md"
    write_file_safe(md_file, content)

    new_content = "New content"

    update_section_in_markdown(
        md_file,
        "## Section",
        new_content,
        create_backup=False
    )

    updated = md_file.read_text()
    # Should have consistent line endings
    assert "\n" in updated

def test_update_result_structure(sample_markdown):
    """Test result dictionary structure."""
    result = update_section_in_markdown(
        sample_markdown,
        "## Architecture",
        "New content",
        create_backup=True
    )

    assert "file" in result
    assert "section" in result
    assert "updated" in result
    assert "backup" in result
    assert "linesChanged" in result

    assert isinstance(result["file"], str)
    assert isinstance(result["section"], str)
    assert isinstance(result["updated"], bool)
    assert isinstance(result["linesChanged"], int)

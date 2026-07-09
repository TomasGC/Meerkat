#!/usr/bin/env python3
"""Tests for update_kanban.py"""

from pathlib import Path

import pytest

from cli.search_kanban import KanbanEntry
from cli.update_kanban import (
    build_entry,
    find_kanban_file,
    insert_entry_at_top,
    update_existing_entry,
)
from common.utils import write_file_safe

def test_find_kanban_file_current_dir(tmp_path):
    """Test finding KANBAN.md in current directory."""
    kanban_file = tmp_path / "KANBAN.md"
    write_file_safe(kanban_file, "# KANBAN")

    result = find_kanban_file(tmp_path)
    assert result == kanban_file

def test_find_kanban_file_claude_dir(tmp_path):
    """Test finding KANBAN.md in .claude directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    kanban_file = claude_dir / "KANBAN.md"
    write_file_safe(kanban_file, "# KANBAN")

    result = find_kanban_file(tmp_path)
    assert result == kanban_file

def test_find_kanban_file_parent_dir(tmp_path):
    """Test finding KANBAN.md in parent directory."""
    kanban_file = tmp_path / "KANBAN.md"
    write_file_safe(kanban_file, "# KANBAN")

    subdir = tmp_path / "subdir"
    subdir.mkdir()

    result = find_kanban_file(subdir)
    assert result == kanban_file

def test_find_kanban_file_not_found(tmp_path):
    """Test when KANBAN.md is not found."""
    # Create an isolated directory with no KANBAN.md and no parent with KANBAN.md
    isolated = tmp_path / "isolated" / "subdir" / "deep"
    isolated.mkdir(parents=True)

    result = find_kanban_file(isolated)
    # Will be None if tmp_path hierarchy has no KANBAN.md
    # (could find parent KANBAN.md if one exists in real filesystem)
    assert result is None or not str(result).startswith(str(isolated))

def test_build_entry_simple():
    """Test building simple entry."""
    entry = build_entry("#123", "Add feature", "- Implemented feature", commits=["abc123f"])

    assert "[#123] Add feature" in entry
    assert "- Implemented feature" in entry
    assert "Commit: abc123f" in entry

def test_build_entry_with_ref():
    """Test building entry with reference."""
    entry = build_entry("#123", "Add feature", "- Implemented feature", ref="https://github.com/org/repo/issues/123")

    assert "Ref: https://github.com/org/repo/issues/123" in entry

def test_build_entry_multiple_refs():
    """Test building entry with multiple references."""
    entry = build_entry(
        "#123",
        "Add feature",
        "- Implemented feature",
        ref="https://github.com/org/repo/issues/123, https://github.com/org/repo/wiki/page"
    )

    assert "Refs:" in entry
    assert "https://github.com/org/repo/issues/123" in entry
    assert "https://github.com/org/repo/wiki/page" in entry

def test_build_entry_multiple_commits():
    """Test building entry with multiple commits."""
    entry = build_entry("#123", "Add feature", "- Implemented feature", commits=["abc123f", "def456g"])

    assert "Commits: abc123f, def456g" in entry

def test_build_entry_date_format():
    """Test that entry includes today's date."""
    entry = build_entry("#123", "Add feature", "- Implemented feature")

    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    assert entry.startswith(today)

def test_update_existing_entry_merge_descriptions():
    """Test merging descriptions in existing entry."""
    existing = KanbanEntry(
        date="2026-03-15",
        issue_id="#123",
        title="Add feature",
        description=["- Implemented core logic"],
        tags=[],
        refs=[],
        commits=["abc123f"],
        raw=""
    )

    updated = update_existing_entry(existing, "- Added tests", ["def456g"])

    assert "- Implemented core logic" in updated
    assert "- Added tests" in updated

def test_update_existing_entry_deduplicate_descriptions():
    """Test deduplicating descriptions."""
    existing = KanbanEntry(
        date="2026-03-15",
        issue_id="#123",
        title="Add feature",
        description=["- Implemented feature"],
        tags=[],
        refs=[],
        commits=[],
        raw=""
    )

    updated = update_existing_entry(existing, "- Implemented feature", [])

    # Should not duplicate
    assert updated.count("- Implemented feature") == 1

def test_update_existing_entry_merge_commits():
    """Test merging commits in existing entry."""
    existing = KanbanEntry(
        date="2026-03-15",
        issue_id="#123",
        title="Add feature",
        description=[],
        tags=[],
        refs=[],
        commits=["abc123f"],
        raw=""
    )

    updated = update_existing_entry(existing, "", ["def456g", "ghi789j"])

    assert "abc123f" in updated
    assert "def456g" in updated
    assert "ghi789j" in updated

def test_update_existing_entry_deduplicate_commits():
    """Test deduplicating commits."""
    existing = KanbanEntry(
        date="2026-03-15",
        issue_id="#123",
        title="Add feature",
        description=[],
        tags=[],
        refs=[],
        commits=["abc123f"],
        raw=""
    )

    updated = update_existing_entry(existing, "", ["abc123f", "def456g"])

    # Should not duplicate abc123f
    assert updated.count("abc123f") == 1

def test_update_existing_entry_update_date():
    """Test that date is updated to today."""
    existing = KanbanEntry(
        date="2026-03-15",
        issue_id="#123",
        title="Add feature",
        description=[],
        tags=[],
        refs=[],
        commits=[],
        raw=""
    )

    updated = update_existing_entry(existing, "- New work", [])

    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    assert updated.startswith(today)

def test_update_existing_entry_preserve_refs():
    """Test that refs are preserved when updating."""
    existing = KanbanEntry(
        date="2026-03-15",
        issue_id="#123",
        title="Add feature",
        description=[],
        tags=[],
        refs=["https://github.com/org/repo/issues/123"],
        commits=[],
        raw=""
    )

    updated = update_existing_entry(existing, "- New work", [])

    assert "Ref: https://github.com/org/repo/issues/123" in updated

def test_insert_entry_at_top():
    """Test inserting entry at top of entries section."""
    content = """# KANBAN

---

2026-03-15 - [#456] Existing entry
- Old work

---

# Backlog
"""

    new_entry = "2026-03-16 - [#123] New entry\n- New work"
    result = insert_entry_at_top(content, new_entry)

    # New entry should be after first --- but before existing
    assert result.index("[#123]") < result.index("[#456]")

def test_insert_entry_at_top_no_separator():
    """Test inserting when no --- separator found."""
    content = "# KANBAN\n\nExisting content"

    new_entry = "2026-03-16 - [#123] New entry\n- New work"
    result = insert_entry_at_top(content, new_entry)

    # New entry should be at the very top
    assert result.startswith("2026-03-16")

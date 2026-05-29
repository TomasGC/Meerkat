#!/usr/bin/env python3
"""Tests for search_kanban.py"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from cli.search_kanban import KanbanEntry, filter_entries, parse_kanban_file
from common.utils import write_file_safe

@pytest.fixture
def sample_kanban(tmp_path):
    """Create a sample KANBAN.md file."""
    content = """# KANBAN

---

2026-03-15 - [#123] Add authentication system
- Implemented JWT authentication
- Added login/logout endpoints
- Created user management UI

tags: #authentication #security
Commits: abc123f, def456g

2026-03-16 - [#456] Fix payment processing bug
- Resolved null pointer in payment handler
- Added validation for payment amounts

tags: #bugfix #payments
Ref: https://github.com/org/repo/issues/456

2026-03-17 - [#12345] Update Docker configuration
- Migrated to multi-stage builds
- Optimized image size

tags: #infrastructure #docker

---

# Backlog

- [#789] Implement notifications
"""

    kanban_file = tmp_path / "KANBAN.md"
    write_file_safe(kanban_file, content)
    return kanban_file

def test_parse_kanban_file(sample_kanban):
    """Test parsing KANBAN.md file."""
    entries = parse_kanban_file(sample_kanban)

    assert len(entries) == 3
    assert entries[0].issue_id == "#123"
    assert entries[0].date == "2026-03-15"
    assert entries[0].title == "Add authentication system"
    assert len(entries[0].description) == 3

def test_parse_kanban_file_extract_tags(sample_kanban):
    """Test extracting tags from entries."""
    entries = parse_kanban_file(sample_kanban)

    assert "authentication" in entries[0].tags
    assert "security" in entries[0].tags
    assert "bugfix" in entries[1].tags
    assert "payments" in entries[1].tags

def test_parse_kanban_file_extract_commits(sample_kanban):
    """Test extracting commits from entries."""
    entries = parse_kanban_file(sample_kanban)

    assert "abc123f" in entries[0].commits
    assert "def456g" in entries[0].commits

def test_parse_kanban_file_extract_refs(sample_kanban):
    """Test extracting references from entries."""
    entries = parse_kanban_file(sample_kanban)

    assert "https://github.com/org/repo/issues/456" in entries[1].refs

def test_parse_kanban_file_azure_ticket(sample_kanban):
    """Test parsing Azure DevOps issue format."""
    entries = parse_kanban_file(sample_kanban)

    assert entries[2].issue_id == "#12345"

def test_parse_kanban_file_nonexistent():
    """Test error when file doesn't exist."""
    with pytest.raises(FileNotFoundError):
        parse_kanban_file(Path("/nonexistent/KANBAN.md"))

def test_parse_kanban_file_empty(tmp_path):
    """Test parsing empty KANBAN.md."""
    kanban_file = tmp_path / "KANBAN.md"
    write_file_safe(kanban_file, "# KANBAN\n\n---\n\n---")

    entries = parse_kanban_file(kanban_file)
    assert entries == []

def test_filter_entries_by_issue(sample_kanban):
    """Test filtering by issue ID."""
    entries = parse_kanban_file(sample_kanban)
    results = filter_entries(entries, issue_id="#123")

    assert len(results) == 1
    assert results[0].issue_id == "#123"

def test_filter_entries_by_tag(sample_kanban):
    """Test filtering by tag."""
    entries = parse_kanban_file(sample_kanban)
    results = filter_entries(entries, tag="payments")

    assert len(results) == 1
    assert results[0].issue_id == "#456"

def test_filter_entries_by_date(sample_kanban):
    """Test filtering by specific date."""
    entries = parse_kanban_file(sample_kanban)
    results = filter_entries(entries, date="2026-03-15")

    assert len(results) == 1
    assert results[0].date == "2026-03-15"

def test_filter_entries_by_date_range(sample_kanban):
    """Test filtering by date range."""
    entries = parse_kanban_file(sample_kanban)
    results = filter_entries(entries, date_from="2026-03-15", date_to="2026-03-16")

    assert len(results) == 2
    assert results[0].date == "2026-03-15"
    assert results[1].date == "2026-03-16"

def test_filter_entries_by_date_from(sample_kanban):
    """Test filtering by start date only."""
    entries = parse_kanban_file(sample_kanban)
    results = filter_entries(entries, date_from="2026-03-16")

    assert len(results) == 2
    assert all(e.date >= "2026-03-16" for e in results)

def test_filter_entries_by_date_to(sample_kanban):
    """Test filtering by end date only."""
    entries = parse_kanban_file(sample_kanban)
    results = filter_entries(entries, date_to="2026-03-16")

    assert len(results) == 2
    assert all(e.date <= "2026-03-16" for e in results)

def test_filter_entries_no_matches(sample_kanban):
    """Test filtering with no matches."""
    entries = parse_kanban_file(sample_kanban)
    results = filter_entries(entries, issue_id="NONEXISTENT")

    assert results == []

def test_filter_entries_multiple_criteria(sample_kanban):
    """Test filtering with multiple criteria."""
    entries = parse_kanban_file(sample_kanban)
    results = filter_entries(entries, tag="authentication", date="2026-03-15")

    assert len(results) == 1
    assert results[0].issue_id == "#123"

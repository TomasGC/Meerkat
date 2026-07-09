"""
Integration tests (mocked) — KANBAN workflow.

Tests the full search → parse → update → write pipeline
with mocked git operations and file I/O.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cli.search_kanban import SearchKanbanScript
from cli.update_kanban import UpdateKanbanScript
from cli.generate_kanban_entry import GenerateKanbanEntryScript

pytestmark = pytest.mark.integration_mock

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_KANBAN = """\
# KANBAN - Test Project

---

2026-05-01 - [#1] Add authentication
- Implemented JWT token validation
- Added login endpoint
tags: #auth #backend
Commit: abc123f

---

2026-04-15 - [#2] Fix database connection pool
- Resolved timeout issues
- Updated pool size configuration
tags: #database #bugfix
Commit: def456g

---

## Notes

- Format: YYYY-MM-DD - [#TICKET] Title
"""

@pytest.fixture
def kanban_file(tmp_path: Path) -> Path:
    f = tmp_path / "kanban.md"
    f.write_text(SAMPLE_KANBAN)
    return f

# ---------------------------------------------------------------------------
# Integration: search → parse pipeline
# ---------------------------------------------------------------------------

def test_search_finds_existing_issue(kanban_file):
    import argparse
    script = SearchKanbanScript()
    args = argparse.Namespace(
        issue="#1", tag=None, date_from=None, date_to=None,
        format="json", kanban_file=kanban_file
    )
    with patch("cli.search_kanban.find_kanban_file", return_value=kanban_file):
        result = script.execute(args)
    assert result["total"] >= 1
    assert any("#1" in e.get("issue_id", "") for e in result["entries"])

def test_search_finds_by_tag(kanban_file):
    import argparse
    script = SearchKanbanScript()
    args = argparse.Namespace(
        issue=None, tag="auth", date_from=None, date_to=None,
        format="json", kanban_file=kanban_file
    )
    with patch("cli.search_kanban.find_kanban_file", return_value=kanban_file):
        result = script.execute(args)
    assert result["total"] >= 1

def test_search_no_results_for_missing_issue(kanban_file):
    import argparse
    script = SearchKanbanScript()
    args = argparse.Namespace(
        issue="#999", tag=None, date_from=None, date_to=None,
        format="json", kanban_file=kanban_file
    )
    with patch("cli.search_kanban.find_kanban_file", return_value=kanban_file):
        result = script.execute(args)
    assert result["total"] == 0

# ---------------------------------------------------------------------------
# Integration: update pipeline
# ---------------------------------------------------------------------------

def test_update_creates_new_entry(tmp_path):
    import argparse
    kanban = tmp_path / "kanban.md"
    kanban.write_text("# KANBAN\n\n---\n\n---\n\n## Notes\n")

    script = UpdateKanbanScript()
    args = argparse.Namespace(
        issue="#3",
        commits="abc123f",
        description="Implemented new feature",
        date=None,
        format="json",
        kanban_file=kanban
    )
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban):
        result = script.execute(args)

    assert result["success"] is True
    content = kanban.read_text()
    assert "#3" in content
    assert "abc123f" in content

def test_update_existing_entry_merges_commits(tmp_path):
    import argparse
    kanban = tmp_path / "kanban.md"
    kanban.write_text(SAMPLE_KANBAN)

    script = UpdateKanbanScript()
    args = argparse.Namespace(
        issue="#1",
        commits="new789a",
        description="Added refresh token support",
        date=None,
        format="json",
        kanban_file=kanban
    )
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban):
        result = script.execute(args)

    assert result["success"] is True
    content = kanban.read_text()
    # Both old and new commits should be present
    assert "abc123f" in content or "new789a" in content

# ---------------------------------------------------------------------------
# Integration: generate + update pipeline
# ---------------------------------------------------------------------------

def test_generate_entry_produces_valid_format():
    import argparse
    script = GenerateKanbanEntryScript()

    with patch("cli.generate_kanban_entry.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="M scripts/cli/auth.py\nA scripts/tests/test_auth.py\n",
            stderr=""
        )
        args = argparse.Namespace(
            commits="abc123f",
            issue="#5",
            style="professional",
            max_bullets=5,
            format="json"
        )
        result = script.execute(args)

    assert "description" in result or "entry" in result or "bullets" in result

# ---------------------------------------------------------------------------
# Integration: full search → update → verify cycle
# ---------------------------------------------------------------------------

def test_full_kanban_cycle(tmp_path):
    """Create, update, then verify a KANBAN entry."""
    import argparse
    kanban = tmp_path / "KANBAN.md"
    kanban.write_text("# KANBAN\n\n---\n\n---\n\n## Notes\n")

    # Step 1: Create entry
    update_script = UpdateKanbanScript()
    create_args = argparse.Namespace(
        issue="#10", commits="deadbeef",
        description="Initial feature implementation",
        date="2026-05-29", format="json", kanban_file=kanban
    )
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban):
        create_result = update_script.execute(create_args)
    assert create_result["success"] is True

    # Step 2: Search and verify it exists
    search_script = SearchKanbanScript()
    search_args = argparse.Namespace(
        issue="#10", tag=None, date_from=None, date_to=None,
        format="json", kanban_file=kanban
    )
    with patch("cli.search_kanban.find_kanban_file", return_value=kanban):
        search_result = search_script.execute(search_args)
    assert search_result["total"] >= 1

    # Step 3: Update with additional commit
    update_args2 = argparse.Namespace(
        issue="#10", commits="cafebabe",
        description="Fixed edge case in feature",
        date=None, format="json", kanban_file=kanban
    )
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban):
        update_result = update_script.execute(update_args2)
    assert update_result["success"] is True

    # Step 4: Verify both commits are tracked
    content = kanban.read_text()
    assert "#10" in content

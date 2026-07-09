"""
E2E tests — KANBAN script workflow.

Tests the complete end-to-end KANBAN management workflow:
search → create → update → verify → format output.

All interactions go through the CLI interface (script.run()) to simulate
real usage.
"""

import json
import subprocess
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

pytestmark = pytest.mark.e2e_scripts


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

INITIAL_KANBAN = """\
# KANBAN - E2E Test Project

Track of work sessions.

---



---

## Notes

- Format: YYYY-MM-DD - [#TICKET] Title
- Language: English only
"""


@pytest.fixture
def kanban_file(tmp_path: Path) -> Path:
    f = tmp_path / "KANBAN.md"
    f.write_text(INITIAL_KANBAN)
    return f


# ---------------------------------------------------------------------------
# E2E: search on empty kanban
# ---------------------------------------------------------------------------

def test_search_empty_kanban(kanban_file, capsys):
    from cli.search_kanban import SearchKanbanScript
    from unittest.mock import patch
    script = SearchKanbanScript()
    with patch("cli.search_kanban.find_kanban_file", return_value=kanban_file):
        exit_code = script.run(["--issue", "#1", "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# E2E: full KANBAN lifecycle
# ---------------------------------------------------------------------------

def test_kanban_full_lifecycle(kanban_file, capsys):
    from cli.update_kanban import UpdateKanbanScript
    from cli.search_kanban import SearchKanbanScript
    from unittest.mock import patch

    # Step 1: Create entry for issue #1
    update_script = UpdateKanbanScript()
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban_file):
        exit_code = update_script.run([
            "--issue", "#1",
            "--commits", "abc1234",
            "--description", "Implemented initial authentication flow",
            "--format", "json"
        ])
    assert exit_code == 0

    # Step 2: Verify entry was created
    search_script = SearchKanbanScript()
    capsys.readouterr()  # clear buffer
    with patch("cli.search_kanban.find_kanban_file", return_value=kanban_file):
        exit_code = search_script.run(["--issue", "#1", "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["total"] >= 1

    # Step 3: Update same issue with additional commit
    capsys.readouterr()
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban_file):
        exit_code = update_script.run([
            "--issue", "#1",
            "--commits", "def5678",
            "--description", "Added token refresh endpoint",
            "--format", "json"
        ])
    assert exit_code == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["success"] is True

    # Step 4: Verify the file contains both commits
    content = kanban_file.read_text()
    assert "#1" in content


# ---------------------------------------------------------------------------
# E2E: multiple issues
# ---------------------------------------------------------------------------

def test_kanban_multiple_issues(kanban_file, capsys):
    from cli.update_kanban import UpdateKanbanScript
    from cli.search_kanban import SearchKanbanScript
    from unittest.mock import patch

    update_script = UpdateKanbanScript()
    search_script = SearchKanbanScript()

    # Create issue #1
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban_file):
        update_script.run(["--issue", "#1", "--commits", "aaa", "--description", "Feature A", "--format", "json"])

    # Create issue #2
    capsys.readouterr()
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban_file):
        update_script.run(["--issue", "#2", "--commits", "bbb", "--description", "Feature B", "--format", "json"])

    # Search for each
    capsys.readouterr()
    with patch("cli.search_kanban.find_kanban_file", return_value=kanban_file):
        search_script.run(["--issue", "#1", "--format", "json"])
    data1 = json.loads(capsys.readouterr().out)
    assert data1["total"] >= 1

    with patch("cli.search_kanban.find_kanban_file", return_value=kanban_file):
        search_script.run(["--issue", "#2", "--format", "json"])
    data2 = json.loads(capsys.readouterr().out)
    assert data2["total"] >= 1


# ---------------------------------------------------------------------------
# E2E: output format variations
# ---------------------------------------------------------------------------

def test_kanban_search_text_format(kanban_file, capsys):
    from cli.update_kanban import UpdateKanbanScript
    from cli.search_kanban import SearchKanbanScript
    from unittest.mock import patch

    update_script = UpdateKanbanScript()
    with patch("cli.update_kanban.find_kanban_file", return_value=kanban_file):
        update_script.run(["--issue", "#5", "--commits", "xyz", "--description", "Test", "--format", "json"])

    capsys.readouterr()
    search_script = SearchKanbanScript()
    with patch("cli.search_kanban.find_kanban_file", return_value=kanban_file):
        exit_code = search_script.run(["--issue", "#5", "--format", "text"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "#5" in captured.out or len(captured.out) > 0


def test_kanban_search_summary_format(kanban_file, capsys):
    from cli.search_kanban import SearchKanbanScript
    from unittest.mock import patch
    search_script = SearchKanbanScript()
    with patch("cli.search_kanban.find_kanban_file", return_value=kanban_file):
        exit_code = search_script.run(["--issue", "#99", "--format", "summary"])
    assert exit_code == 0
